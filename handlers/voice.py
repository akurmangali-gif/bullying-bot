"""
Обработчик голосовых сообщений.
Транскрибирует через Groq Whisper (бесплатно, тот же ключ).
Поддерживает: voice (кружочки), audio (файлы .mp3/.m4a).
"""

import os
import logging
import tempfile
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from openai import AsyncOpenAI

from config import AI_API_KEY, AI_BASE_URL
from handlers.states import Survey, Triage
from handlers.assessment import AssessmentState

logger = logging.getLogger(__name__)
router = Router()


async def transcribe_audio(file_path: str) -> str:
    """Отправляет аудио в Groq Whisper и возвращает текст."""
    client = AsyncOpenAI(
        api_key=AI_API_KEY,
        base_url=AI_BASE_URL,
    )
    with open(file_path, "rb") as f:
        transcription = await client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language="ru",
            response_format="text",
        )
    return transcription.strip() if isinstance(transcription, str) else transcription.text.strip()


async def handle_voice_message(message: Message, state: FSMContext):
    """Общий обработчик: скачивает аудио, транскрибирует, обрабатывает как текст."""

    if not AI_API_KEY or AI_API_KEY in ("вставьте_ключ_groq_сюда", ""):
        await message.answer("⚠️ Голосовые сообщения не поддерживаются — AI ключ не настроен.")
        return

    # Определяем тип файла
    voice = message.voice or message.audio
    if not voice:
        return

    thinking = await message.answer("🎙 Распознаю голосовое сообщение...")

    try:
        # Скачиваем во временный файл
        bot = message.bot
        file_info = await bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        await bot.download_file(file_info.file_path, destination=tmp_path)

        # Транскрибируем
        text = await transcribe_audio(tmp_path)

    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        await thinking.delete()
        await message.answer(
            "⚠️ Не удалось распознать голосовое. "
            "Попробуйте написать текстом или отправить ещё раз."
        )
        return
    finally:
        # Удаляем временный файл
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    await thinking.delete()

    if not text:
        await message.answer("⚠️ Не удалось разобрать речь. Попробуйте говорить чётче или напишите текстом.")
        return

    # Показываем что услышали
    await message.answer(
        f"🎙 <b>Я услышал:</b>\n<i>«{text}»</i>\n\n⏳ Обрабатываю...",
        parse_mode="HTML"
    )

    # Создаём фейковое текстовое сообщение и передаём в нужный обработчик
    current_state = await state.get_state()

    if current_state == AssessmentState.waiting_for_situation.state:
        # Пользователь описывал ситуацию голосом
        from handlers.assessment import process_situation
        message.text = text
        await process_situation(message, state)

    elif current_state in (Survey.incident_description.state, Survey.witnesses.state):
        # Пользователь заполнял анкету голосом
        message.text = text
        if current_state == Survey.incident_description.state:
            from handlers.survey import survey_description
            await survey_description(message, state)
        else:
            from handlers.survey import survey_witnesses_text
            await survey_witnesses_text(message, state)

    else:
        # Состояние неизвестно — запускаем правовую оценку по умолчанию
        await state.set_state(AssessmentState.waiting_for_situation)
        message.text = text
        from handlers.assessment import process_situation
        await process_situation(message, state)


# ── Регистрация хендлеров ─────────────────────────────────────────────────

@router.message(F.voice)
async def on_voice(message: Message, state: FSMContext):
    await handle_voice_message(message, state)


@router.message(F.audio)
async def on_audio(message: Message, state: FSMContext):
    await handle_voice_message(message, state)
