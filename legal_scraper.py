"""
Скрапер законодательства РК с adilet.zan.kz.

Скачивает ключевые НПА по теме буллинга и сохраняет в legal_docs/.
Запускать вручную при обновлении законодательства:
    python3 legal_scraper.py

Документы сохраняются в репозиторий — бот использует их напрямую.
Не нужно перекачивать при каждом запуске.
"""

import re
import time
import logging
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

LEGAL_DOCS_DIR = Path(__file__).parent / "legal_docs"
LEGAL_DOCS_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

# ── Список документов для скачивания ─────────────────────────────────────────

DOCUMENTS = [
    {
        "id": "pravila_506",
        "name": "Правила профилактики травли (буллинга) ребёнка — Приказ МП РК №506",
        "urls": [
            "https://adilet.zan.kz/rus/docs/V2200031180",  # регистр. №31180
        ],
    },
    {
        "id": "pravila_506_izm_2024",
        "name": "Изменения в Правила №506 (2024, действует с 25.08.2024)",
        "urls": [
            "https://adilet.zan.kz/rus/docs/V2400034817",
        ],
    },
    {
        "id": "appk",
        "name": "АППК РК — Административный процедурно-процессуальный кодекс",
        "urls": [
            "https://adilet.zan.kz/rus/docs/K2000000350",
            "https://www.adilet.zan.kz/rus/docs/K2000000350",
        ],
    },
    {
        "id": "uk_rk",
        "name": "Уголовный кодекс Республики Казахстан",
        "urls": [
            "https://adilet.zan.kz/rus/docs/K1400000226",
        ],
    },
    {
        "id": "prava_rebyonka",
        "name": "Закон РК О правах ребёнка в Республике Казахстан",
        "urls": [
            "https://adilet.zan.kz/rus/docs/Z020000345_",
        ],
    },
]

# ── Статьи АППК которые нас интересуют ───────────────────────────────────────
APPK_TARGET_ARTICLES = ["64", "65", "91", "92", "93"]

# ── Статьи УК которые нас интересуют ─────────────────────────────────────────
UK_TARGET_ARTICLES = ["15", "108-1", "109-1", "115", "194"]


def fetch_document(url: str):
    """Скачивает HTML страницу документа с adilet.kz."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.warning(f"Не удалось загрузить {url}: {e}")
        return None


def extract_text_from_adilet(html: str, doc_name: str) -> str:
    """Извлекает текст документа из HTML страницы adilet.kz."""
    soup = BeautifulSoup(html, "html.parser")

    # Убираем навигацию, меню, скрипты
    for tag in soup.select("nav, header, footer, script, style, .menu, "
                           ".header, .footer, .navigation, .breadcrumb, "
                           ".tabs, .tab-content > :not(.active)"):
        tag.decompose()

    # Основной контент документа
    content_selectors = [
        "#documentText",
        ".document-text",
        ".doc-text",
        "#content",
        ".content",
        "main",
        "article",
    ]

    content = None
    for selector in content_selectors:
        element = soup.select_one(selector)
        if element and len(element.get_text(strip=True)) > 500:
            content = element
            break

    if not content:
        content = soup.body or soup

    # Получаем текст
    text = content.get_text(separator="\n", strip=True)

    # Чистим — убираем множественные пробелы и пустые строки
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    clean_text = "\n".join(lines)

    # Убираем дублирующиеся строки навигации
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)

    return f"=== {doc_name} ===\n\n{clean_text}"


def extract_articles(full_text: str, article_numbers: list[str]) -> str:
    """Извлекает только нужные статьи из большого кодекса."""
    result_parts = []
    lines = full_text.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        # Ищем заголовки статей
        for art_num in article_numbers:
            patterns = [
                rf"Статья\s+{re.escape(art_num)}\b",
                rf"Статья\s+{re.escape(art_num)}-",
                rf"^{re.escape(art_num)}\.",
            ]
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Собираем текст статьи (до следующей статьи)
                    article_lines = [line]
                    j = i + 1
                    while j < len(lines) and j < i + 150:  # макс 150 строк на статью
                        next_line = lines[j]
                        # Стоп — новая статья
                        if re.match(r"Статья\s+\d+", next_line, re.IGNORECASE):
                            break
                        article_lines.append(next_line)
                        j += 1
                    result_parts.append("\n".join(article_lines))
                    break
        i += 1

    if result_parts:
        return "\n\n---\n\n".join(result_parts)
    return full_text  # если не нашли — возвращаем всё


def scrape_and_save(doc: dict) -> bool:
    """Скачивает один документ и сохраняет в legal_docs/."""
    logger.info(f"Загружаю: {doc['name']}")

    html = None
    for url in doc["urls"]:
        html = fetch_document(url)
        if html:
            logger.info(f"  ✓ Успешно: {url}")
            break
        time.sleep(1)

    if not html:
        logger.error(f"  ✗ Не удалось загрузить ни по одному URL")
        return False

    text = extract_text_from_adilet(html, doc["name"])

    # Для кодексов — извлекаем только нужные статьи
    if doc["id"] == "appk":
        text = extract_articles(text, APPK_TARGET_ARTICLES)
        header = f"=== {doc['name']} ===\n(Извлечены статьи: {', '.join(APPK_TARGET_ARTICLES)})\n\n"
        text = header + text

    elif doc["id"] == "uk_rk":
        text = extract_articles(text, UK_TARGET_ARTICLES)
        header = f"=== {doc['name']} ===\n(Извлечены статьи: {', '.join(UK_TARGET_ARTICLES)})\n\n"
        text = header + text

    # Сохраняем
    out_path = LEGAL_DOCS_DIR / f"{doc['id']}.txt"
    out_path.write_text(text, encoding="utf-8")
    logger.info(f"  → Сохранено: {out_path} ({len(text):,} символов)")
    return True


def main():
    logger.info("=== Обновление правовой базы с adilet.zan.kz ===\n")
    success = 0
    failed = []

    for doc in DOCUMENTS:
        ok = scrape_and_save(doc)
        if ok:
            success += 1
        else:
            failed.append(doc["name"])
        time.sleep(2)  # вежливая пауза между запросами

    logger.info(f"\n=== Готово: {success}/{len(DOCUMENTS)} документов ===")
    if failed:
        logger.warning(f"Не загружены: {', '.join(failed)}")
        logger.info("Попробуйте запустить снова или добавьте тексты вручную в legal_docs/")


if __name__ == "__main__":
    main()
