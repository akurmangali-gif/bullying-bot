"""
Обработчик голосовых сообщений.

После распознавания — автоматически вызывает нужный обработчик.
Пользователю показывается только короткое подтверждение,
следующий вопрос появляется сразу без лишних действий.
"""

import io
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from openai import AsyncOpenAI

from config import AI_API_KEY, AI_BASE_URL
from handlers.states import Survey
from handlers.assessment import AssessmentState

logger = logging.getLogger(__name__)
router = Router()


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Транскрибирует аудио из памяти через Groq Whisper (без записи на диск)."""
    client = AsyncOpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "voice.ogg"
    transcription = await client.audio.transcriptions.create(
        model="whisper-large-v3",
        file=audio_file,
        language="ru",
        response_format="text",
    )
    return transcription.strip() if isinstance(transcription, str) else transcription.text.strip()


async def handle_voice_message(message: Message, state: FSMContext):
    if not AI_API_KEY or AI_API_KEY in ("вставьте_ключ_groq_сюда", ""):
        await message.answer("⚠️ Голосовые сообщения не поддерживаются — AI ключ не настроен.")
        return

    voice = message.voice or message.audio
    if not voice:
        return

    # Мгновенный статус — пользователь видит реакцию сразу
    thinking = await message.answer("🎙 Распознаю...")

    try:
        bot = message.bot
        file_info = await bot.get_file(voice.file_id)
        buf = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=buf)
        buf.seek(0)
        audio_bytes = buf.read()
        text = await transcribe_audio(audio_bytes)
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        await thinking.delete()
        await message.answer("⚠️ Не удалось распознать. Попробуйте ещё раз или напишите текстом.")
        return

    await thinking.delete()

    if not text:
        await message.answer("⚠️ Речь не разобрана. Говорите чётче или напишите текстом.")
        return

    # Показываем что услышали — коротко, без призыва к действию
    await message.answer(f"✅ <i>«{text}»</i>", parse_mode="HTML")

    # Создаём копию Message с подставленным текстом
    # (Message — Pydantic-модель, прямое присвоение не работает)
    try:
        msg = message.model_copy(update={"text": text})
    except AttributeError:
        msg = message.copy(update={"text": text})

    current_state = await state.get_state()

    if current_state == AssessmentState.waiting_for_situation.state:
        from handlers.assessment import process_situation
        await process_situation(msg, state)

    elif current_state == Survey.applicant_name.state:
        from handlers.survey import survey_applicant_name
        await survey_applicant_name(msg, state)

    elif current_state == Survey.child_and_school.state:
        from handlers.survey import survey_child_and_school
        await survey_child_and_school(msg, state)

    elif current_state == Survey.incident_description.state:
        from handlers.survey import survey_description
        await survey_description(msg, state)

    else:
        # В остальных состояниях (кнопочных) голос не нужен — подсказываем
        await message.answer("👆 На этом шаге используйте кнопки выше.")


# ── Регистрация хендлеров ─────────────────────────────────────────────────

@router.message(F.voice)
async def on_voice(message: Message, state: FSMContext):
    await handle_voice_message(message, state)


@router.message(F.audio)
async def on_audio(message: Message, state: FSMContext):
    await handle_voice_message(message, state)
