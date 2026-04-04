"""
Обработчик заявок на консультацию ADDASTRA.
Кнопка "Получить консультацию юриста" → сохраняем лид → уведомляем администратора.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import SUPPORT_CONTACT, ADMIN_CHAT_ID
from db import save_lead

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "consult_addastra")
async def handle_consult_request(call: CallbackQuery):
    await call.answer()
    await call.message.edit_reply_markup()

    user = call.from_user
    username = f"@{user.username}" if user.username else f"id:{user.id}"
    full_name = user.full_name or ""

    # Сохраняем лид в БД
    try:
        await save_lead(user_id=user.id, username=username, applicant_name=full_name)
    except Exception as e:
        logger.error(f"save_lead error: {e}")

    # Уведомляем администратора
    if ADMIN_CHAT_ID:
        try:
            await call.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                text=(
                    "🔔 <b>Новая заявка на консультацию!</b>\n\n"
                    f"👤 Telegram: {username}\n"
                    f"📛 Имя: {full_name}\n"
                    f"🆔 Chat ID: <code>{user.id}</code>"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Admin notify error: {e}")

    await call.message.answer(
        "✅ <b>Заявка принята!</b>\n\n"
        "Юрист ADDASTRA свяжется с вами в течение рабочего дня.\n\n"
        f"Если срочно — напишите напрямую: {SUPPORT_CONTACT}",
        parse_mode="HTML",
    )
