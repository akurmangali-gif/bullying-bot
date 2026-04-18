"""
Обработчик правовой оценки.

Сценарий:
  /assess → пользователь пишет ситуацию → LLM даёт оценку →
  предлагает сгенерировать документы
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ai_service import get_legal_assessment

router = Router()


class AssessmentState(StatesGroup):
    waiting_for_situation = State()
    after_assessment = State()


# ── Вход через команду /assess ────────────────────────────────────────────

@router.message(Command("assess"))
async def cmd_assess(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AssessmentState.waiting_for_situation)
    await message.answer(
        "⚖️ <b>Предварительная правовая оценка</b>\n\n"
        "Опишите ситуацию своими словами — что происходит, когда началось, "
        "кто участвует, сколько лет обидчику, что уже делали.\n\n"
        "<i>Чем подробнее — тем точнее оценка. "
        "Можно писать как угодно, без формальностей.</i>",
        parse_mode="HTML",
    )


# ── Также запускается кнопкой из главного меню ────────────────────────────

@router.callback_query(F.data == "start_assess")
async def btn_assess(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await state.set_state(AssessmentState.waiting_for_situation)
    await call.message.answer(
        "⚖️ <b>Предварительная правовая оценка</b>\n\n"
        "Опишите ситуацию своими словами — что происходит, когда началось, "
        "кто участвует, сколько лет обидчику, что уже делали.\n\n"
        "<i>Чем подробнее — тем точнее оценка.</i>",
        parse_mode="HTML",
    )


# ── Получаем описание → отправляем в LLM ─────────────────────────────────

@router.message(AssessmentState.waiting_for_situation)
async def process_situation(message: Message, state: FSMContext):
    if message.text:
        text = message.text.strip()
    else:
        data = await state.get_data()
        text = data.get("_voice_text", "").strip()
        if text:
            await state.update_data(_voice_text=None)

    if len(text) < 20:
        await message.answer(
            "✏️ Пожалуйста, опишите подробнее — хотя бы 2-3 предложения."
        )
        return

    await state.update_data(situation_text=text)

    # Показываем что думаем
    thinking = await message.answer("🔍 Анализирую ситуацию по законодательству РК...")

    assessment = await get_legal_assessment(text)

    # Удаляем сообщение "анализирую"
    await thinking.delete()

    # Отправляем оценку
    await message.answer(assessment, parse_mode="HTML")

    # Предлагаем следующий шаг
    await state.set_state(AssessmentState.after_assessment)
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 Сгенерировать документы", callback_data="go_to_docs")
    kb.button(text="🔄 Описать другую ситуацию", callback_data="new_assess")
    kb.button(text="🏠 В главное меню", callback_data="main_menu")
    kb.adjust(1)

    await message.answer(
        "Что делаем дальше?",
        reply_markup=kb.as_markup(),
    )


# ── После оценки — кнопки ─────────────────────────────────────────────────

@router.callback_query(F.data == "go_to_docs")
async def go_to_docs(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    # Уровень уже определён в триаже — пропускаем его, идём прямо в анкету
    data = await state.get_data()
    if not data.get("triage_level"):
        await state.update_data(triage_level="GREEN")
    # Ситуация уже описана — переносим в поле анкеты, чтобы не спрашивать повторно
    if data.get("situation_text") and not data.get("incident_description"):
        await state.update_data(incident_description=data["situation_text"])
    from handlers.triage import start_survey
    await call.message.answer(
        "📋 Отлично! Заполним короткую анкету для документов — всего 4 шага."
    )
    await start_survey(call.message, state)


@router.callback_query(F.data == "new_assess")
async def new_assess(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    await state.set_state(AssessmentState.waiting_for_situation)
    await call.message.answer(
        "✏️ Опишите новую ситуацию:"
    )


@router.callback_query(F.data == "main_menu")
async def main_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    await state.clear()
    await show_main_menu(call.message)


async def show_main_menu(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="⚖️ Получить правовую оценку", callback_data="start_assess")
    kb.button(text="📄 Сразу к документам", callback_data="start_docs")
    kb.adjust(1)
    await message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите с чего начать:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML",
    )
