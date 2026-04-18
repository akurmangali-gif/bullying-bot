"""
Фоновый планировщик напоминаний о сроках реагирования школы.
Запускается как asyncio task при старте бота.
"""
import asyncio
import logging

from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import get_due_reminders, mark_reminder_sent

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 3600  # проверка раз в час


def _reminder_message(level: int) -> tuple[str, object]:
    """Возвращает (текст, клавиатура) для напоминания уровня 1 или 2."""
    if level == 1:
        text = (
            "⏰ <b>Прошло 5 дней с момента подачи заявления</b>\n\n"
            "По АППК РК школа обязана была зарегистрировать обращение "
            "в день подачи и дать письменный ответ.\n\n"
            "Если ответа <b>нет</b> — самое время потребовать его официально.\n"
            "Нажмите /start и выберите <b>«Сгенерировать документы»</b> → "
            "получите <b>Документ 2: Требование письменного ответа</b>.\n\n"
            "Если ответ получен — отлично! Напишите /start для нового обращения."
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="📄 Получить Документ 2", callback_data="start_docs")
        return text, kb.as_markup()

    else:  # level == 2
        text = (
            "⏰ <b>Прошло 10 дней — школа так и не ответила?</b>\n\n"
            "Если письменного ответа от школы до сих пор нет — "
            "следующий шаг: <b>жалоба в акимат / отдел образования</b>.\n\n"
            "Нажмите /start → «Сгенерировать документы» → получите "
            "<b>Документ 4: Жалоба в акимат</b>.\n\n"
            "Или позвоните юристу ADDASTRA: <b>+7 776 138 00 00</b>"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="📄 Получить Документ 4 (акимат)", callback_data="start_docs")
        kb.button(text="💼 Консультация юриста", callback_data="consult_addastra")
        kb.adjust(1)
        return text, kb.as_markup()


async def reminder_loop(bot: Bot):
    """Запускается один раз при старте — крутится бесконечно."""
    logger.info("Scheduler started — checking reminders every %ds", INTERVAL_SECONDS)
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        try:
            due = await get_due_reminders()
            if due:
                logger.info("Sending %d reminder(s)", len(due))
            for r in due:
                text, markup = _reminder_message(r["level"])
                try:
                    await bot.send_message(
                        chat_id=r["user_id"],
                        text=text,
                        reply_markup=markup,
                        parse_mode="HTML",
                    )
                    await mark_reminder_sent(r["id"])
                except Exception as e:
                    # Пользователь мог заблокировать бота — не критично
                    logger.warning("Reminder %d failed for user %d: %s", r["id"], r["user_id"], e)
                    await mark_reminder_sent(r["id"])  # помечаем чтобы не повторять
        except Exception as e:
            logger.error("Scheduler error: %s", e)
