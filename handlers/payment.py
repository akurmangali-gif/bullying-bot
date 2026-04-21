"""
Ручной платёжный флоу через Kaspi (MVP).

Сценарий:
  1. Пользователь получает Doc 1 (бесплатно) в generate_and_send()
  2. Бот показывает кнопки выбора пакета (Базовый / Полный)
  3. Пользователь нажимает → бот показывает реквизиты Kaspi + просит скриншот
  4. Пользователь присылает фото/документ чека
  5. Бот форвардит скриншот администратору с кнопками [✅ Подтвердить] [❌ Отклонить]
  6. Администратор нажимает ✅ → бот генерирует и отправляет оплаченные документы
     (Basic: Docs 2-3, Full: Docs 2-4 + создаёт напоминания)
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import KASPI_CARD, ADMIN_CHAT_ID
from db import get_case_by_id, create_reminders

logger = logging.getLogger(__name__)
router = Router()

PACKAGES = {
    "b": {"name": "Базовый",  "price": 3900, "docs": 3, "reminders": False},
    "f": {"name": "Полный",   "price": 5900, "docs": 5, "reminders": True},
}


class PaymentState(StatesGroup):
    waiting_screenshot = State()


# ── Пользователь выбрал пакет ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_"))
async def on_package_select(call: CallbackQuery, state: FSMContext):
    """pay_b_{case_id} или pay_f_{case_id}"""
    await call.answer()
    await call.message.edit_reply_markup()

    parts = call.data.split("_")          # ["pay", "b", "123"]
    if len(parts) < 3:
        return
    pkg_key  = parts[1]                   # "b" или "f"
    case_id  = int(parts[2])
    pkg      = PACKAGES.get(pkg_key)
    if not pkg:
        return

    await state.update_data(
        payment_pkg=pkg_key,
        payment_case_id=case_id,
    )
    await state.set_state(PaymentState.waiting_screenshot)

    card_line = f"\n💳 <b>Карта Kaspi:</b> <code>{KASPI_CARD}</code>" if KASPI_CARD else ""
    await call.message.answer(
        f"💳 <b>Оплата — пакет «{pkg['name']}» ({pkg['price']} тг)</b>\n"
        f"{card_line}\n\n"
        f"<b>Как оплатить:</b>\n"
        f"1. Переведите <b>{pkg['price']} тг</b> на карту Kaspi выше\n"
        f"2. Сделайте скриншот подтверждения\n"
        f"3. Отправьте скриншот следующим сообщением\n\n"
        f"<i>После подтверждения оплаты документы придут автоматически — "
        f"обычно в течение нескольких минут.</i>\n\n"
        f"Отменить: /cancel",
        parse_mode="HTML",
    )


# ── Пользователь прислал скриншот ────────────────────────────────────────

@router.message(PaymentState.waiting_screenshot, F.photo | F.document)
async def on_payment_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    pkg_key  = data.get("payment_pkg")
    case_id  = data.get("payment_case_id")
    pkg      = PACKAGES.get(pkg_key, {})

    user     = message.from_user
    username = f"@{user.username}" if user.username else f"id:{user.id}"

    if not ADMIN_CHAT_ID:
        logger.error("ADMIN_CHAT_ID не задан — оплата не может быть подтверждена")
        await message.answer(
            "⚠️ Скриншот получен, но система подтверждения не настроена.\n"
            "Напишите нам: +7 776 138 00 00 (ADDASTRA) — подтвердим вручную.",
        )
        return

    # Кнопки для администратора
    kb = InlineKeyboardBuilder()
    kb.button(
        text=f"✅ Подтвердить {pkg.get('name', '')} {pkg.get('price', '')} тг",
        callback_data=f"adm_ok_{pkg_key}_{user.id}_{case_id}",
    )
    kb.button(
        text="❌ Отклонить",
        callback_data=f"adm_no_{user.id}",
    )
    kb.adjust(1)

    # Форвардим фото/документ администратору
    caption = (
        f"💰 <b>Заявка на оплату!</b>\n\n"
        f"👤 {username} | {user.full_name}\n"
        f"📦 Пакет: <b>{pkg.get('name')} — {pkg.get('price')} тг</b>\n"
        f"📋 Кейс #{case_id}"
    )

    try:
        if message.photo:
            await message.bot.send_photo(
                chat_id=int(ADMIN_CHAT_ID),
                photo=message.photo[-1].file_id,
                caption=caption,
                reply_markup=kb.as_markup(),
                parse_mode="HTML",
            )
        else:
            await message.bot.send_document(
                chat_id=int(ADMIN_CHAT_ID),
                document=message.document.file_id,
                caption=caption,
                reply_markup=kb.as_markup(),
                parse_mode="HTML",
            )
    except Exception as e:
        logger.error(f"Не удалось отправить скриншот администратору: {e}")

    await message.answer(
        "✅ <b>Скриншот получен!</b>\n\n"
        "Мы проверим оплату и отправим документы в течение нескольких минут.\n\n"
        "<i>Если возникнут вопросы: +7 776 138 00 00 (ADDASTRA)</i>",
        parse_mode="HTML",
    )
    # Очищаем только state оплаты, не трогаем остальные данные
    await state.set_state(None)


# ── Пользователь прислал текст вместо скриншота ───────────────────────────

@router.message(PaymentState.waiting_screenshot)
async def on_payment_wrong_format(message: Message, state: FSMContext):
    await message.answer(
        "📸 Ожидаю <b>скриншот оплаты</b> — фото или документ.\n\n"
        "Если хотите отменить — нажмите /cancel",
        parse_mode="HTML",
    )


# ── Администратор: подтвердить оплату ─────────────────────────────────────

@router.callback_query(F.data.startswith("adm_ok_"))
async def admin_confirm_payment(call: CallbackQuery, bot: Bot):
    """adm_ok_{pkg}_{user_id}_{case_id}"""
    if ADMIN_CHAT_ID and str(call.from_user.id) != str(ADMIN_CHAT_ID):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    await call.answer("✅ Подтверждаю...")
    await call.message.edit_reply_markup()

    parts = call.data.split("_")          # ["adm", "ok", pkg, uid, cid]
    if len(parts) < 5:
        await call.message.answer("⚠️ Ошибка формата callback")
        return

    pkg_key  = parts[2]
    user_id  = int(parts[3])
    case_id  = int(parts[4])
    pkg      = PACKAGES.get(pkg_key, {})

    # Получаем данные кейса из БД
    case_data = await get_case_by_id(case_id)
    if not case_data:
        await call.message.answer(f"⚠️ Кейс #{case_id} не найден в БД")
        await bot.send_message(
            user_id,
            "⚠️ Возникла техническая ошибка. Пожалуйста, свяжитесь с нами: +7 776 138 00 00",
        )
        return

    # Генерируем документы
    from handlers.documents import (
        make_doc2_written_response,
        make_doc3_cyberbullying_memo,
        make_doc4_akimat_complaint,
        make_doc5_police_complaint,
    )
    import os

    docs_to_send = []

    docs_to_send.append((make_doc2_written_response(case_data), "📄 Документ 2: Требование письменного ответа"))
    docs_to_send.append((make_doc3_cyberbullying_memo(case_data), "📄 Документ 3: Памятка по фиксации кибербуллинга"))
    if pkg.get("docs", 3) >= 4:
        docs_to_send.append((make_doc4_akimat_complaint(case_data), "📄 Документ 4: Жалоба в акимат"))
    if pkg.get("docs", 3) >= 5:
        docs_to_send.append((make_doc5_police_complaint(case_data), "📄 Документ 5: Заявление в полицию (ст. 127-2 КОАП РК)"))

    # Отправляем документы пользователю
    await bot.send_message(
        user_id,
        f"✅ <b>Оплата подтверждена! Пакет «{pkg.get('name')}»</b>\n\n"
        f"Отправляю ваши документы:",
        parse_mode="HTML",
    )

    for path, label in docs_to_send:
        try:
            await bot.send_message(user_id, label, parse_mode="HTML")
            await bot.send_document(user_id, FSInputFile(path))
            os.remove(path)
        except Exception as e:
            logger.error(f"Ошибка отправки {path} пользователю {user_id}: {e}")

    # Создаём напоминания для полного пакета
    if pkg.get("reminders"):
        await create_reminders(user_id, case_id)
        await bot.send_message(
            user_id,
            "⏰ <b>Напоминания о сроках активированы</b>\n\n"
            "Бот напомнит вам на 5-й и 10-й день:\n"
            "• День 5 — проверить ответ школы\n"
            "• День 10 — при необходимости подать жалобу в акимат",
            parse_mode="HTML",
        )

    # Финальное сообщение пользователю
    await bot.send_message(
        user_id,
        "👨‍⚖️ <b>Нужна помощь юриста?</b>\n\n"
        "Если ситуация сложная — звоните: <b>+7 776 138 00 00</b> (ADDASTRA).\n\n"
        "/start — новое обращение",
        parse_mode="HTML",
    )

    # Уведомляем администратора об успехе
    await call.message.answer(
        f"✅ Документы пакета «{pkg.get('name')}» отправлены пользователю {user_id} (кейс #{case_id})"
    )


# ── Администратор: отклонить оплату ──────────────────────────────────────

@router.callback_query(F.data.startswith("adm_no_"))
async def admin_reject_payment(call: CallbackQuery, bot: Bot):
    if ADMIN_CHAT_ID and str(call.from_user.id) != str(ADMIN_CHAT_ID):
        await call.answer("⛔ Нет доступа", show_alert=True)
        return

    await call.answer("❌ Отклонено")
    await call.message.edit_reply_markup()

    parts = call.data.split("_")          # ["adm", "no", uid]
    user_id = int(parts[2]) if len(parts) >= 3 else None

    if user_id:
        await bot.send_message(
            user_id,
            "❌ <b>Оплата не подтверждена</b>\n\n"
            "Возможно, скриншот не соответствует сумме или произошла ошибка перевода.\n\n"
            "Свяжитесь с нами для уточнения: <b>+7 776 138 00 00</b> (ADDASTRA)",
            parse_mode="HTML",
        )

    await call.message.answer(
        f"❌ Оплата пользователя {user_id} отклонена — уведомление отправлено."
    )
