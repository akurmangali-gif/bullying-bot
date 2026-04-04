import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN
from db import init_db
from handlers import triage, survey
from handlers import assessment as assessment_handler
from handlers import voice as voice_handler
from handlers import leads as leads_handler

logging.basicConfig(level=logging.INFO)


# ── Главное меню ──────────────────────────────────────────────────────────

def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⚖️ Правовая оценка ситуации (AI)", callback_data="start_assess")
    kb.button(text="📄 Сразу сгенерировать документы", callback_data="start_docs")
    kb.adjust(1)
    return kb.as_markup()


async def send_welcome(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>Буллинг Стоп КЗ</b>\n\n"
        "Помогу защитить права вашего ребёнка при буллинге в школе "
        "по закону РК (Приказ МП РК № 506).\n\n"
        "🆕 <b>Новое:</b> теперь бот даёт предварительную <b>правовую оценку</b> "
        "ситуации на основе законодательства РК — просто опишите что произошло.\n\n"
        "⚠️ <i>Бот предоставляет процедурный маршрут и шаблоны документов. "
        "Это не юридическая консультация.</i>",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )


# ── Роутер для /start и главного меню ────────────────────────────────────

from aiogram import Router
main_router = Router()


@main_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await send_welcome(message, state)


@main_router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📌 <b>Команды бота:</b>\n\n"
        "/start — главное меню\n"
        "/assess — правовая оценка ситуации (AI)\n"
        "/docs — сгенерировать документы\n"
        "/help — эта справка\n\n"
        "По вопросам: @addastra",
        parse_mode="HTML",
    )


@main_router.message(Command("docs"))
async def cmd_docs(message: Message, state: FSMContext):
    await state.clear()
    from handlers.triage import ask_q1
    await ask_q1(message, state)


@main_router.callback_query(F.data == "start_docs")
async def btn_start_docs(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup()
    await state.clear()
    from handlers.triage import ask_q1
    await ask_q1(call.message, state)


# ── Запуск ────────────────────────────────────────────────────────────────

async def main():
    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN не задан. Скопируйте .env.example в .env и заполните токен."
        )

    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Порядок важен: main_router первым (перехватывает /start)
    dp.include_router(main_router)
    dp.include_router(leads_handler.router)    # глобальные callback без state
    dp.include_router(voice_handler.router)    # голосовые — до текстовых
    dp.include_router(assessment_handler.router)
    dp.include_router(triage.router)
    dp.include_router(survey.router)

    logging.info("Бот запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
