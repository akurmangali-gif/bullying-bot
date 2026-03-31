"""
Модуль правовой базы — загружает НПА из legal_docs/ и формирует контекст для LLM.

Принцип: документы хранятся как текстовые файлы в репозитории.
При запросе — подбираем релевантные секции и включаем в промпт.
Никакого vector DB, никаких embeddings — работает быстро на любом железе.
"""

import re
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

LEGAL_DOCS_DIR = Path(__file__).parent / "legal_docs"

# ── Ключевые слова для тематической фильтрации ────────────────────────────────

TOPIC_KEYWORDS = {
    "bullying_school": [
        "травля", "буллинг", "профилактика", "506", "совет профилактики",
        "журнал учёта", "организация образования", "школа", "обидчик",
        "жертва", "систематическ", "запугивание", "унижение",
    ],
    "admin_procedure": [
        "аппк", "административн", "обращение", "регистрация", "приём",
        "обжалование", "жалоба", "срок", "ответ", "уведомлен",
        "статья 64", "статья 91", "статья 92",
    ],
    "criminal": [
        "уголовн", "ук рк", "побои", "насилие", "угроза", "вымогательство",
        "статья 109", "статья 115", "статья 194", "несовершеннолетн",
        "возраст ответственности", "14 лет", "16 лет",
    ],
    "child_rights": [
        "права ребёнка", "защита прав", "законный представитель",
        "несовершеннолетний", "безопасность", "достоинство",
    ],
}


@lru_cache(maxsize=None)
def load_all_docs() -> dict[str, str]:
    """Загружает все документы из legal_docs/ в память (кэшируется)."""
    docs = {}
    if not LEGAL_DOCS_DIR.exists():
        logger.warning(f"Папка legal_docs/ не найдена. Запустите: python3 legal_scraper.py")
        return docs

    for path in sorted(LEGAL_DOCS_DIR.glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8")
            docs[path.stem] = text
            logger.info(f"Загружен: {path.name} ({len(text):,} символов)")
        except Exception as e:
            logger.error(f"Ошибка загрузки {path.name}: {e}")

    if not docs:
        logger.warning("Правовая база пуста! Запустите: python3 legal_scraper.py")
    else:
        logger.info(f"Правовая база: {len(docs)} документов загружено")

    return docs


def _score_relevance(text: str, query_lower: str) -> float:
    """Считает релевантность текста запросу по ключевым словам."""
    score = 0.0
    text_lower = text.lower()

    # Совпадение с запросом пользователя
    query_words = re.findall(r'\w+', query_lower)
    for word in query_words:
        if len(word) > 3 and word in text_lower:
            score += 1.0

    # Совпадение по тематическим блокам
    for topic, keywords in TOPIC_KEYWORDS.items():
        topic_hits = sum(1 for kw in keywords if kw in text_lower)
        if topic_hits > 0:
            score += topic_hits * 0.5

    return score


def get_relevant_legal_context(situation_text: str, max_chars: int = 12000) -> str:
    """
    Возвращает релевантные части законодательства для данной ситуации.

    max_chars: максимальный размер контекста (12000 ≈ ~3000 токенов)
    Groq поддерживает 128k — можно безопасно включать весь контекст.
    """
    docs = load_all_docs()
    if not docs:
        return ""

    query_lower = situation_text.lower()
    scored_docs = []

    for doc_id, doc_text in docs.items():
        score = _score_relevance(doc_text[:5000], query_lower)
        scored_docs.append((score, doc_id, doc_text))

    # Сортируем по релевантности
    scored_docs.sort(key=lambda x: x[0], reverse=True)

    # Собираем контекст — сначала самые релевантные
    context_parts = []
    total_chars = 0

    # Правила №506 всегда включаем первыми (главный документ)
    priority_docs = ["pravila_506", "pravila_506_izm_2024"]
    for doc_id in priority_docs:
        if doc_id in docs:
            text = docs[doc_id]
            if total_chars + len(text) <= max_chars:
                context_parts.append(text)
                total_chars += len(text)

    # Остальные по релевантности
    for score, doc_id, doc_text in scored_docs:
        if doc_id in priority_docs:
            continue
        if score < 1.0:
            continue
        if total_chars + len(doc_text) > max_chars:
            # Добавляем обрезанный вариант
            remaining = max_chars - total_chars
            if remaining > 500:
                context_parts.append(doc_text[:remaining] + "\n[... документ обрезан ...]")
            break
        context_parts.append(doc_text)
        total_chars += len(doc_text)

    if not context_parts:
        return ""

    return "\n\n" + "=" * 60 + "\n".join(context_parts) + "\n" + "=" * 60


def get_legal_context_summary() -> str:
    """Возвращает краткий список загруженных документов (для логов)."""
    docs = load_all_docs()
    if not docs:
        return "Правовая база не загружена"
    lines = [f"  • {doc_id}: {len(text):,} символов" for doc_id, text in docs.items()]
    return "Правовая база:\n" + "\n".join(lines)
