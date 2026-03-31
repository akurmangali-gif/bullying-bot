from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.states import Survey
from config import SUPPORT_CONTACT

router = Router()

SKIP = "skip"


def skip_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Пропустить", callback_data=SKIP)
    return kb.as_markup()


def age_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="До 14 лет", callback_data="age_under14")
    kb.button(text="14–15 лет", callback_data="age_14_15")
    kb.button(text="16+ лет", callback_data="age_16plus")
    kb.button(text="Не знаю", callback_data="age_unknown")
    kb.adjust(2)
    return kb.as_markup()


def evidence_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Есть (фото/скриншоты/справки)", callback_data="ev_yes")
    kb.button(text="❌ Нет пока", callback_data="ev_no")
    kb.adjust(1)
    return kb.as_markup()


def prior_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Нет, впервые обращаюсь", callback_data="prior_none")
    kb.button(text="Устно говорил(а) с учителем", callback_data="prior_verbal")
    kb.button(text="Подавал(а) письменное заявление", callback_data="prior_written")
    kb.adjust(1)
    return kb.as_markup()


# ── Step 1: ФИО заявителя ──────────────────────────────────────────────────

@router.message(Survey.applicant_name)
async def survey_applicant_name(message: Message, state: FSMContext):
    await state.update_data(applicant_name=message.text.strip())
    await state.set_state(Survey.child_name)
    await message.answer(
        "📝 <b>Шаг 2 из 11</b>\n\nПолное <b>ФИО ребёнка</b>:",
        parse_mode="HTML",
    )


# ── Step 2: ФИО ребёнка ───────────────────────────────────────────────────

@router.message(Survey.child_name)
async def survey_child_name(message: Message, state: FSMContext):
    await state.update_data(child_name=message.text.strip())
    await state.set_state(Survey.child_class)
    await message.answer(
        "📝 <b>Шаг 3 из 11</b>\n\n<b>Класс</b> (например: 5А, 7Б):",
        parse_mode="HTML",
    )


# ── Step 3: Класс ─────────────────────────────────────────────────────────

@router.message(Survey.child_class)
async def survey_child_class(message: Message, state: FSMContext):
    await state.update_data(child_class=message.text.strip())
    await state.set_state(Survey.school_name)
    await message.answer(
        "📝 <b>Шаг 4 из 11</b>\n\n<b>Полное название школы</b> "
        "(например: КГУ «СОШ №15»):",
        parse_mode="HTML",
    )


# ── Step 4: Школа ─────────────────────────────────────────────────────────

@router.message(Survey.school_name)
async def survey_school_name(message: Message, state: FSMContext):
    await state.update_data(school_name=message.text.strip())
    await state.set_state(Survey.city)
    await message.answer(
        "📝 <b>Шаг 5 из 11</b>\n\n<b>Город / населённый пункт</b>:",
        parse_mode="HTML",
    )


# ── Step 5: Город ─────────────────────────────────────────────────────────

@router.message(Survey.city)
async def survey_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await state.set_state(Survey.bully_age_group)
    await message.answer(
        "📝 <b>Шаг 6 из 11</b>\n\n<b>Возраст обидчика</b> (это важно для выбора правового трека):",
        reply_markup=age_kb(),
        parse_mode="HTML",
    )


# ── Step 6: Возраст обидчика ──────────────────────────────────────────────

@router.callback_query(Survey.bully_age_group)
async def survey_bully_age(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    labels = {
        "age_under14": "До 14 лет",
        "age_14_15": "14–15 лет",
        "age_16plus": "16+ лет",
        "age_unknown": "Не известно",
    }
    await state.update_data(bully_age_group=labels.get(call.data, call.data))
    await state.set_state(Survey.incident_dates)
    await call.message.answer(
        "📝 <b>Шаг 7 из 11</b>\n\n<b>Даты эпизодов</b> (когда происходило):\n"
        "Например: <i>15 марта 2026, 20 марта 2026</i>",
        parse_mode="HTML",
    )


# ── Step 7: Даты ──────────────────────────────────────────────────────────

@router.message(Survey.incident_dates)
async def survey_dates(message: Message, state: FSMContext):
    await state.update_data(incident_dates=message.text.strip())
    await state.set_state(Survey.incident_description)
    await message.answer(
        "📝 <b>Шаг 8 из 11</b>\n\n<b>Опишите ситуацию</b> — что происходило, где, кто участвовал.\n"
        "<i>Чем точнее описание — тем убедительнее документ.</i>",
        parse_mode="HTML",
    )


# ── Step 8: Описание ──────────────────────────────────────────────────────

@router.message(Survey.incident_description)
async def survey_description(message: Message, state: FSMContext):
    await state.update_data(incident_description=message.text.strip())
    await state.set_state(Survey.witnesses)
    await message.answer(
        "📝 <b>Шаг 9 из 11</b>\n\n<b>Свидетели</b> (ФИО или «одноклассники», «учитель Иванова И.И.»).\n"
        "Если нет — нажмите «Пропустить».",
        reply_markup=skip_kb(),
        parse_mode="HTML",
    )


# ── Step 9: Свидетели ─────────────────────────────────────────────────────

@router.message(Survey.witnesses)
async def survey_witnesses_text(message: Message, state: FSMContext):
    await state.update_data(witnesses=message.text.strip())
    await ask_evidence(message, state)


@router.callback_query(Survey.witnesses)
async def survey_witnesses_skip(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    await state.update_data(witnesses="не указаны")
    await ask_evidence(call.message, state)


async def ask_evidence(message: Message, state: FSMContext):
    await state.set_state(Survey.has_evidence)
    await message.answer(
        "📝 <b>Шаг 10 из 11</b>\n\n<b>Есть ли у вас доказательства?</b>\n"
        "(скриншоты переписки, фото повреждений, медицинские справки)",
        reply_markup=evidence_kb(),
        parse_mode="HTML",
    )


# ── Step 10: Доказательства ───────────────────────────────────────────────

@router.callback_query(Survey.has_evidence)
async def survey_evidence(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    label = "Есть (фото/скриншоты/справки)" if call.data == "ev_yes" else "Отсутствуют на данный момент"
    await state.update_data(has_evidence=label)
    await state.set_state(Survey.prior_actions)
    await call.message.answer(
        "📝 <b>Шаг 11 из 11</b>\n\n<b>Что уже было сделано?</b>",
        reply_markup=prior_kb(),
        parse_mode="HTML",
    )


# ── Step 11: Предыдущие действия ──────────────────────────────────────────

@router.callback_query(Survey.prior_actions)
async def survey_prior(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    labels = {
        "prior_none": "Обращаюсь впервые",
        "prior_verbal": "Устно говорил(а) с учителем/администрацией",
        "prior_written": "Подавал(а) письменное заявление в школу",
    }
    await state.update_data(prior_actions=labels.get(call.data, call.data))
    await show_confirm(call.message, state)


async def show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(Survey.confirm)

    summary = (
        "✅ <b>Проверьте данные перед генерацией документов:</b>\n\n"
        f"👤 Заявитель: {data.get('applicant_name')}\n"
        f"👦 Ребёнок: {data.get('child_name')}, {data.get('child_class')} класс\n"
        f"🏫 Школа: {data.get('school_name')}, {data.get('city')}\n"
        f"🎯 Возраст обидчика: {data.get('bully_age_group')}\n"
        f"📅 Даты: {data.get('incident_dates')}\n"
        f"📝 Ситуация: {data.get('incident_description')[:200]}{'…' if len(data.get('incident_description',''))>200 else ''}\n"
        f"👥 Свидетели: {data.get('witnesses')}\n"
        f"📎 Доказательства: {data.get('has_evidence')}\n"
        f"📋 Ранее: {data.get('prior_actions')}\n\n"
        f"⚡ Уровень ситуации: <b>{data.get('triage_level')}</b>"
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

    # Передаём управление генератору документов
    from handlers.documents import generate_and_send
    await generate_and_send(call.message, state)
