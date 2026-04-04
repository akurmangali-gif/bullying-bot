"""
Анкета для генерации документов — 4 шага вместо 11.

Шаг 1: ФИО заявителя
Шаг 2: ФИО ребёнка + класс + школа + город (одним сообщением, LLM-парсинг)
Шаг 3: Описание ситуации (когда и что случилось)
Шаг 4: Возраст обидчика (кнопки) → что уже делали (кнопки)
"""

import json
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from openai import AsyncOpenAI

from handlers.states import Survey
from config import SUPPORT_CONTACT, AI_API_KEY, AI_BASE_URL

router = Router()
logger = logging.getLogger(__name__)


def age_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="До 14 лет", callback_data="age_under14")
    kb.button(text="14–15 лет", callback_data="age_14_15")
    kb.button(text="16+ лет", callback_data="age_16plus")
    kb.button(text="Не знаю", callback_data="age_unknown")
    kb.adjust(2)
    return kb.as_markup()


def prior_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Нет, обращаюсь впервые", callback_data="prior_none")
    kb.button(text="Устно говорил(а) с учителем", callback_data="prior_verbal")
    kb.button(text="Подавал(а) письменное заявление", callback_data="prior_written")
    kb.adjust(1)
    return kb.as_markup()


async def _parse_child_and_school(text: str) -> dict:
    """
    Использует LLM для извлечения полей из свободного текста.
    Например: «Иванов Денис, 7А класс, СОШ №15, Алматы»
    Возвращает: {child_name, child_class, school_name, city}
    """
    try:
        client = AsyncOpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Извлеки из текста пользователя 4 поля и верни ТОЛЬКО JSON без пояснений:\n"
                        '{"child_name": "ФИО ребёнка", "child_class": "класс", '
                        '"school_name": "название школы", "city": "город"}\n'
                        "Если поле не указано — пустая строка."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=150,
        )
        raw = response.choices[0].message.content.strip()
        # Извлекаем JSON если есть лишний текст
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception as e:
        logger.warning(f"LLM parse error: {e}")

    # Fallback: простой split по запятой
    parts = [p.strip() for p in text.split(",")]
    return {
        "child_name": parts[0] if len(parts) > 0 else text,
        "child_class": parts[1] if len(parts) > 1 else "",
        "school_name": parts[2] if len(parts) > 2 else "",
        "city": parts[3] if len(parts) > 3 else "",
    }


async def _get_text(message: Message, state: FSMContext) -> str:
    """Возвращает текст сообщения или голосовой транскрипт из state."""
    if message.text:
        return message.text.strip()
    data = await state.get_data()
    voice = data.get("_voice_text", "")
    if voice:
        await state.update_data(_voice_text=None)
    return voice.strip()


# ── Шаг 1: ФИО заявителя ─────────────────────────────────────────────────

@router.message(Survey.applicant_name)
async def survey_applicant_name(message: Message, state: FSMContext):
    text = await _get_text(message, state)
    if not text:
        return
    await state.update_data(applicant_name=text)
    await state.set_state(Survey.child_and_school)
    await message.answer(
        "📝 <b>Шаг 2 из 4</b>\n\n"
        "Скажите или напишите одним сообщением:\n"
        "<b>ФИО ребёнка, класс, школа и город</b>\n\n"
        "<i>Пример: «Иванов Денис, 7А класс, СОШ №15, Алматы»</i>",
        parse_mode="HTML",
    )


# ── Шаг 2: ФИО ребёнка + класс + школа + город ───────────────────────────

@router.message(Survey.child_and_school)
async def survey_child_and_school(message: Message, state: FSMContext):
    raw = await _get_text(message, state)
    if not raw:
        return
    await state.update_data(child_and_school_raw=raw)

    # Парсим через LLM
    fields = await _parse_child_and_school(raw)
    await state.update_data(
        child_name=fields.get("child_name", raw),
        child_class=fields.get("child_class", ""),
        school_name=fields.get("school_name", ""),
        city=fields.get("city", ""),
    )

    # Если ситуация уже описана (пришли из правовой оценки) — пропускаем шаг 3
    data = await state.get_data()
    if data.get("incident_description"):
        await state.set_state(Survey.bully_age_group)
        await message.answer(
            "📝 <b>Шаг 3 из 4</b>\n\n"
            "✅ Описание ситуации уже получено из вашего обращения.\n\n"
            "<b>Возраст обидчика</b> (важно для выбора правового трека):",
            reply_markup=age_kb(),
            parse_mode="HTML",
        )
    else:
        await state.set_state(Survey.incident_description)
        await message.answer(
            "📝 <b>Шаг 3 из 4</b>\n\n"
            "<b>Опишите ситуацию</b> — когда это началось, что происходило, "
            "кто участвовал.\n\n"
            "<i>Можно голосом или текстом. Чем подробнее — тем убедительнее документ.</i>",
            parse_mode="HTML",
        )


# ── Шаг 3: Описание ситуации ──────────────────────────────────────────────

@router.message(Survey.incident_description)
async def survey_description(message: Message, state: FSMContext):
    text = await _get_text(message, state)
    if not text:
        return
    await state.update_data(incident_description=text)
    await state.set_state(Survey.bully_age_group)
    await message.answer(
        "📝 <b>Шаг 4 из 4</b>\n\n"
        "<b>Возраст обидчика</b> (важно для выбора правового трека):",
        reply_markup=age_kb(),
        parse_mode="HTML",
    )


# ── Шаг 4а: Возраст обидчика ─────────────────────────────────────────────

@router.callback_query(Survey.bully_age_group)
async def survey_bully_age(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    labels = {
        "age_under14": "До 14 лет",
        "age_14_15":   "14–15 лет",
        "age_16plus":  "16+ лет",
        "age_unknown": "Не известно",
    }
    await state.update_data(bully_age_group=labels.get(call.data, call.data))
    await state.set_state(Survey.prior_actions)
    await call.message.answer(
        "📝 <b>Последний вопрос</b>\n\n"
        "<b>Что уже делали?</b>",
        reply_markup=prior_kb(),
        parse_mode="HTML",
    )


# ── Шаг 4б: Предыдущие действия ──────────────────────────────────────────

@router.callback_query(Survey.prior_actions)
async def survey_prior(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    labels = {
        "prior_none":    "Обращаюсь впервые",
        "prior_verbal":  "Устно говорил(а) с учителем/администрацией",
        "prior_written": "Подавал(а) письменное заявление в школу",
    }
    await state.update_data(prior_actions=labels.get(call.data, call.data))
    await show_confirm(call.message, state)


# ── Подтверждение ─────────────────────────────────────────────────────────

async def show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(Survey.confirm)

    child_line = data.get("child_name", "")
    if data.get("child_class"):
        child_line += f", {data['child_class']} класс"

    school_line = data.get("school_name", "")
    if data.get("city"):
        school_line += f", {data['city']}"

    desc = data.get("incident_description", "")
    desc_preview = desc[:200] + ("…" if len(desc) > 200 else "")

    summary = (
        "✅ <b>Проверьте данные:</b>\n\n"
        f"👤 Заявитель: {data.get('applicant_name', '—')}\n"
        f"👦 Ребёнок: {child_line or '—'}\n"
        f"🏫 Школа: {school_line or '—'}\n"
        f"🎯 Возраст обидчика: {data.get('bully_age_group', '—')}\n"
        f"📝 Ситуация: {desc_preview or '—'}\n"
        f"📋 Ранее: {data.get('prior_actions', '—')}\n\n"
        f"⚡ Уровень: <b>{ {'RED':'🔴 Экстренный','AMBER':'🟡 Серьёзный','GREEN':'🟢 Школьный'}.get(data.get('triage_level','GREEN'),'🟢 Школьный') }</b>"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Всё верно — создать документы", callback_data="confirm_yes")
    kb.button(text="🔄 Начать заново", callback_data="confirm_restart")
    kb.adjust(1)

    await message.answer(summary, reply_markup=kb.as_markup(), parse_mode="HTML")


@router.callback_query(Survey.confirm)
async def survey_confirm(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()

    if call.data == "confirm_restart":
        await state.clear()
        await call.message.answer("Начинаем заново. Введите /start")
        return

    from handlers.documents import generate_and_send
    await generate_and_send(call.message, state)
