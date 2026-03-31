"""
Обработчик голосовых сообщений.
Транскрибирует через Groq Whisper и перенаправляет в нужный обработчик.
Работает во ВСЕХ текстовых состояниях анкеты (все 9 шагов).
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
    """Скачивает аудио в память, транскрибирует, перенаправляет в нужный обработчик."""

    if not AI_API_KEY or AI_API_KEY in ("вставьте_ключ_groq_сюда", ""):
        await message.answer("⚠️ Голосовые сообщения не поддерживаются — AI ключ не настроен.")
        return

    voice = message.voice or message.audio
    if not voice:
        return

    # Показываем статус сразу
    thinking = await message.answer("🎙 Распознаю...")

    try:
        # Скачиваем в память (быстрее чем на диск)
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
        await message.answer(
            "⚠️ Не удалось распознать. Попробуйте ещё раз или напишите текстом."
        )
        return

    await thinking.delete()

    if not text:
        await message.answer("⚠️ Речь не разобрана. Говорите чётче или напишите текстом.")
        return

    # Показываем что услышали
    await message.answer(f"🎙 <b>Услышал:</b> <i>«{text}»</i>", parse_mode="HTML")

    # Инжектируем текст в message и вызываем нужный обработчик
    message.text = text
    current_state = await state.get_state()

    # Все текстовые состояния анкеты + оценка
    if current_state == AssessmentState.waiting_for_situation.state:
        from handlers.assessment import process_situation
        await process_situation(message, state)

    elif current_state == Survey.applicant_name.state:
        from handlers.survey import survey_applicant_name
        await survey_applicant_name(message, state)

    elif current_state == Survey.child_name.state:
        from handlers.survey import survey_child_name
        await survey_child_name(message, state)

    elif current_state == Survey.child_class.state:
        from handlers.survey import survey_child_class
        await survey_child_class(message, state)

    elif current_state == Survey.school_name.state:
        from handlers.survey import survey_school_name
        await survey_school_name(message, state)

    elif current_state == Survey.city.state:
        from handlers.survey import survey_city
        await survey_city(message, state)

    elif current_state == Survey.incident_dates.state:
        from handlers.survey import survey_dates
        await survey_dates(message, state)

    elif current_state == Survey.incident_description.state:
        from handlers.survey import survey_description
        await survey_description(message, state)

    elif current_state == Survey.witnesses.state:
        from handlers.survey import survey_witnesses_text
        await survey_witnesses_text(message, state)

    else:
        # Состояние неизвестно — запускаем правовую оценку по умолчанию
        await state.set_state(AssessmentState.waiting_for_situation)
        from handlers.assessment import process_situation
        await process_situation(message, state)


# ── Регистрация хендлеров ─────────────────────────────────────────────────

@router.message(F.voice)
async def on_voice(message: Message, state: FSMContext):
    await handle_voice_message(message, state)


@router.message(F.audio)
async def on_audio(message: Message, state: FSMContext):
    await handle_voice_message(message, state)
