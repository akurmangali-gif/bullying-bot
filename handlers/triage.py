from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.states import Triage, Survey

router = Router()

YES = "yes"
NO = "no"


def yn_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да", callback_data=YES)
    kb.button(text="❌ Нет", callback_data=NO)
    kb.adjust(2)
    return kb.as_markup()


DISCLAIMER = (
    "💡 Помогаем родителям защитить детей — разбираемся в законах и готовим документы.\n"
    "⚠️ <i>Бот не оказывает юридических услуг и не гарантирует конкретный результат. "
    "Для сложных ситуаций рядом есть юристы ADDASTRA.</i>"
)

INTRO = (
    "👋 Привет! Я помогу вам защитить права вашего ребёнка при буллинге "
    "в школе — по закону РК (Приказ МП РК № 506).\n\n"
    "Я задам несколько вопросов и подготовлю пакет документов.\n\n"
    + DISCLAIMER
)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(INTRO, parse_mode="HTML")
    await ask_q1(message, state)


async def ask_q1(message: Message, state: FSMContext):
    await state.set_state(Triage.q1_life_risk)
    await message.answer(
        "🚨 <b>Вопрос 1 из 3 — Оценка срочности</b>\n\n"
        "Есть ли <b>прямая угроза жизни или здоровью</b>?\n"
        "(травмы, оружие, угрозы расправой, суицидальные высказывания)",
        reply_markup=yn_kb(),
        parse_mode="HTML",
    )


@router.callback_query(Triage.q1_life_risk, F.data.in_([YES, NO]))
async def triage_q1(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()

    if call.data == YES:
        await state.update_data(triage_level="RED")
        await show_red_alert(call.message, state)
        return

    await state.set_state(Triage.q2_violence)
    await call.message.answer(
        "⚠️ <b>Вопрос 2 из 3</b>\n\n"
        "Есть ли <b>физическое насилие, вымогательство, кибербуллинг</b> "
        "или другие серьёзные действия?",
        reply_markup=yn_kb(),
        parse_mode="HTML",
    )


@router.callback_query(Triage.q2_violence, F.data.in_([YES, NO]))
async def triage_q2(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()

    if call.data == YES:
        await state.update_data(triage_level="AMBER")
        await show_amber_info(call.message)
    else:
        await state.update_data(triage_level="GREEN")

    await state.set_state(Triage.q3_systematic)
    await call.message.answer(
        "📋 <b>Вопрос 3 из 3</b>\n\n"
        "Это происходило <b>систематически (2 и более раз)</b>?\n"
        "(важно для официальной квалификации как «буллинг» по Правилам № 506)",
        reply_markup=yn_kb(),
        parse_mode="HTML",
    )


@router.callback_query(Triage.q3_systematic, F.data.in_([YES, NO]))
async def triage_q3(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()

    data = await state.get_data()
    systematic = call.data == YES
    await state.update_data(systematic=systematic)

    level = data.get("triage_level", "GREEN")
    await call.message.answer(
        f"✅ Уровень ситуации определён: <b>{level_label(level)}</b>\n\n"
        + level_advice(level, systematic)
        + "\n\nТеперь заполним анкету для подготовки документов. Это займёт ~3 минуты.",
        parse_mode="HTML",
    )
    await start_survey(call.message, state)


def level_label(level: str) -> str:
    return {"RED": "🔴 Экстренный", "AMBER": "🟡 Серьёзный", "GREEN": "🟢 Школьный"}.get(level, level)


def level_advice(level: str, systematic: bool) -> str:
    if level == "RED":
        return ""
    if level == "AMBER":
        base = ("🟡 <b>Рекомендация:</b> Параллельно подайте документы в школу "
                "<b>и</b> обратитесь в полицию (102).\n"
                "Если обидчику <b>14–15 лет</b> — уголовная ответственность возможна "
                "по ст.15 УК РК (убийство, вымогательство, разбой и др.).\n"
                "Если <b>до 14 лет</b> — основной трек через школу и управление образования.")
    else:
        base = ("🟢 <b>Рекомендация:</b> Действуем через школьную процедуру по Правилам № 506: "
                "заявление директору → Совет профилактики → при необходимости управление образования.")

    if not systematic:
        base += ("\n\n⚠️ Эпизод <b>один раз</b> — школа обязана реагировать на признаки травли, "
                 "но официальная квалификация «буллинга» требует систематичности (2+ раза).")
    return base


async def show_red_alert(message: Message, state: FSMContext):
    await message.answer(
        "🔴 <b>ЭКСТРЕННАЯ СИТУАЦИЯ</b>\n\n"
        "1. Обеспечьте <b>немедленную безопасность</b> ребёнка\n"
        "2. При травмах — вызовите <b>скорую (103)</b>\n"
        "3. При угрозах / оружии — вызовите <b>полицию (102)</b>\n"
        "4. Получите медицинские справки — это ваши ключевые доказательства\n\n"
        "После того как ситуация под контролем — <b>вернитесь</b> и продолжите оформление "
        "документов для школы и управление образованияа.\n\n"
        "Введите /start чтобы начать анкету.",
        parse_mode="HTML",
    )
    await state.clear()


async def show_amber_info(message: Message):
    await message.answer(
        "🟡 <b>Важно для вашей ситуации</b>\n\n"
        "При физическом насилии или вымогательстве — <b>параллельно</b> подайте заявление в полицию.\n"
        "Школьная процедура <b>не заменяет</b> уголовно-правовую защиту.\n\n"
        "Документы, которые подготовит бот, нужны <b>для обоих треков</b>.",
        parse_mode="HTML",
    )


async def start_survey(message: Message, state: FSMContext):
    await state.set_state(Survey.applicant_name)
    await message.answer(
        "📝 <b>Шаг 1 из 4</b>\n\n"
        "Ваше <b>полное ФИО</b> (заявитель — родитель/законный представитель):",
        parse_mode="HTML",
    )
