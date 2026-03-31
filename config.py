import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "bullying_bot.db")
GENERATED_DIR = os.getenv("GENERATED_DIR", "generated")
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@your_support_username")

# ── AI / LLM настройки ────────────────────────────────────────────────────
# Для теста (бесплатно): Groq — https://console.groq.com → API Keys
# Для своего LLM:        AI_BASE_URL=http://ВАШ_СЕРВЕР:8000/v1
#                        AI_API_KEY=любой_текст (если не нужна авторизация)
#                        AI_MODEL=название_вашей_модели
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1")
AI_API_KEY  = os.getenv("AI_API_KEY", "")
AI_MODEL    = os.getenv("AI_MODEL", "llama-3.3-70b-versatile")
