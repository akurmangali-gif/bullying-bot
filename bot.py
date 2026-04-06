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
    kb.button(text="⚖️ Правовая оценка ситуации", callback_data="start_assess")
    kb.button(text="📄 Сразу сгенерировать документы", callback_data="start_docs")
    kb.adjust(1)
    return kb.as_markup()


async def send_welcome(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>Буллинг Стоп КЗ</b>\n\n"
        "Ребёнка обижают в школе? Напишите или 🎤 надиктуйте что происходит — "
        "за 5 минут получите правовую оценку и готовые документы для школы.\n\n"
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
        "/assess — правовая оценка ситуации\n"
        "/docs — сгенерировать документы\n"
        "/feedback — оставить отзыв\n"
        "/privacy — политика конфиденциальности\n"
        "/terms — условия использования\n"
        "/help — эта справка\n\n"
        "По вопросам: @addastra",
        parse_mode="HTML",
    )


@main_router.message(Command("privacy"))
async def cmd_privacy(message: Message):
    await message.answer(
        "🔒 <b>Политика конфиденциальности</b>\n"
        "Буллинг Стоп КЗ (@bulling_help_kz_bot)\n"
        "Дата: 06.04.2026\n\n"
        "<b>1. Какие данные собираем</b>\n"
        "При обращении через бот мы получаем: имя законного представителя, имя и класс ребёнка, "
        "название школы, город, описание ситуации, Telegram ID. "
        "Данные передаются вами добровольно.\n\n"
        "<b>2. Зачем используем</b>\n"
        "Исключительно для формирования документов и, при вашем запросе, "
        "передачи заявки юристу ADDASTRA.\n\n"
        "<b>3. Кому передаём</b>\n"
        "Данные не передаются третьим лицам. Исключение: вы сами запросили "
        "консультацию юриста — тогда ваш контакт получает ADDASTRA (ТОО «ADDASTRA»).\n\n"
        "<b>4. Хранение</b>\n"
        "Данные хранятся на защищённом сервере. Срок хранения — 1 год, "
        "после чего удаляются. По запросу удаляем досрочно.\n\n"
        "<b>5. Ваши права</b>\n"
        "Вы вправе запросить, исправить или удалить свои данные. "
        "Запрос отправьте в поддержку: @addastra\n\n"
        "<b>6. Правовая основа</b>\n"
        "Закон РК «О персональных данных и их защите» от 21.05.2013 № 94-V.\n\n"
        "Используя бот, вы соглашаетесь с настоящей политикой.",
        parse_mode="HTML",
    )


@main_router.message(Command("terms"))
async def cmd_terms(message: Message):
    await message.answer(
        "📄 <b>Условия использования (Публичная оферта)</b>\n"
        "Буллинг Стоп КЗ | ТОО «ADDASTRA»\n"
        "Дата: 06.04.2026\n\n"
        "<b>1. Предмет</b>\n"
        "Бот предоставляет шаблоны юридических документов и процедурные рекомендации "
        "по законодательству РК в сфере защиты детей от буллинга.\n\n"
        "<b>2. Что входит в услугу</b>\n"
        "— Документ 1 (Заявление директору) — бесплатно\n"
        "— Документы 2–3 (Требование ответа + Памятка) — 2 990 тг за пакет\n"
        "— Консультация юриста ADDASTRA — по отдельному договору\n\n"
        "<b>3. Что не входит</b>\n"
        "Бот не оказывает юридических услуг, не представляет интересы в госорганах, "
        "не гарантирует конкретный результат. Документы являются шаблонами.\n\n"
        "<b>4. Оплата</b>\n"
        "Оплата за пакет документов производится через Kaspi Pay. "
        "Возврат возможен до момента отправки документов.\n\n"
        "<b>5. Ответственность</b>\n"
        "Исполнитель не несёт ответственности за действия (бездействие) "
        "государственных органов и школ после подачи документов.\n\n"
        "<b>6. Акцепт</b>\n"
        "Использование бота означает принятие настоящей оферты.\n\n"
        "Вопросы: @addastra",
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


@main_router.message(Command("feedback"))
async def cmd_feedback(message: Message, state: FSMContext):
    from aiogram.fsm.state import State, StatesGroup
    await message.answer(
        "💬 <b>Оставьте отзыв или сообщите об ошибке</b>\n\n"
        "Напишите следующим сообщением — что понравилось, что можно улучшить, "
        "или опишите ошибку если что-то пошло не так.\n\n"
        "<i>Мы читаем каждый отзыв.</i>",
        parse_mode="HTML",
    )
    await state.set_state(FeedbackState.waiting)


from aiogram.fsm.state import State, StatesGroup as _SG

class FeedbackState(_SG):
    waiting = State()


@main_router.message(FeedbackState.waiting)
async def receive_feedback(message: Message, state: FSMContext):
    text = message.text or message.caption or ""
    user = message.from_user
    username = f"@{user.username}" if user.username else f"id:{user.id}"

    # Уведомляем администратора
    if ADMIN_CHAT_ID:
        try:
            await message.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                text=(
                    "📬 <b>Новый отзыв!</b>\n\n"
                    f"👤 {username} | {user.full_name}\n\n"
                    f"💬 {text}"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

    await state.clear()
    await message.answer(
        "✅ Спасибо! Ваш отзыв получен.\n\n"
        "Введите /start чтобы вернуться в главное меню.",
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
