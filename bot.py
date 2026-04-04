import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import aiosqlite
from config import BOT_TOKEN, DB_PATH, ADMIN_CHAT_ID
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
        "<i>Помогаем родителям защитить детей — разбираемся в законах и готовим документы.</i>",
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


@main_router.message(Command("stats"))
async def cmd_stats(message: Message):
    if ADMIN_CHAT_ID and str(message.from_user.id) != str(ADMIN_CHAT_ID):
        return  # молча игнорируем — чужие не узнают что команда вообще есть

    async with aiosqlite.connect(DB_PATH) as db:
        (total_cases,)   = await (await db.execute("SELECT COUNT(*) FROM cases")).fetchone()
        (today_cases,)   = await (await db.execute(
            "SELECT COUNT(*) FROM cases WHERE DATE(created_at)=DATE('now')"
        )).fetchone()
        (week_cases,)    = await (await db.execute(
            "SELECT COUNT(*) FROM cases WHERE created_at >= DATE('now','-7 days')"
        )).fetchone()
        (total_leads,)   = await (await db.execute("SELECT COUNT(*) FROM leads")).fetchone()
        (today_leads,)   = await (await db.execute(
            "SELECT COUNT(*) FROM leads WHERE DATE(created_at)=DATE('now')"
        )).fetchone()
        level_rows = await (await db.execute(
            "SELECT triage_level, COUNT(*) FROM cases GROUP BY triage_level"
        )).fetchall()

    level_map = {"GREEN": "🟢 Школьный", "AMBER": "🟡 Серьёзный", "RED": "🔴 Экстренный"}
    level_text = "\n".join(
        f"  {level_map.get(lvl, lvl)}: {cnt}" for lvl, cnt in level_rows
    ) or "  нет данных"

    await message.answer(
        "📊 <b>Статистика бота</b>\n\n"
        f"📋 Обращений всего: <b>{total_cases}</b>\n"
        f"  — сегодня: {today_cases}\n"
        f"  — за 7 дней: {week_cases}\n\n"
        f"По уровням:\n{level_text}\n\n"
        f"💼 Заявок на консультацию ADDASTRA:\n"
        f"  всего: <b>{total_leads}</b>, сегодня: {today_leads}",
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
