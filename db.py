import aiosqlite
from datetime import datetime, timedelta
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                applicant_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                triage_level TEXT NOT NULL,
                city TEXT,
                bully_age_group TEXT,
                prior_actions TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                case_id INTEGER NOT NULL,
                remind_at DATETIME NOT NULL,
                level INTEGER NOT NULL,
                sent INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def save_case(user_id: int, data: dict) -> int:
    """Сохраняем только анонимную аналитику — без персональных данных."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO cases (
                user_id, triage_level, city, bully_age_group, prior_actions
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            data.get("triage_level"),
            data.get("city"),
            data.get("bully_age_group"),
            data.get("prior_actions"),
        ))
        await db.commit()
        return cursor.lastrowid


async def save_lead(user_id: int, username: str, applicant_name: str = "") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO leads (user_id, username, applicant_name) VALUES (?, ?, ?)",
            (user_id, username or "", applicant_name),
        )
        await db.commit()
        return cursor.lastrowid


# ── Напоминания (трекер сроков) ───────────────────────────────────────────

async def create_reminders(user_id: int, case_id: int):
    """Создаёт 2 напоминания: на 5-й и 10-й день после подачи заявления."""
    now = datetime.utcnow()
    remind_5  = now + timedelta(days=5)
    remind_10 = now + timedelta(days=10)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reminders (user_id, case_id, remind_at, level) VALUES (?, ?, ?, ?)",
            (user_id, case_id, remind_5.isoformat(), 1),
        )
        await db.execute(
            "INSERT INTO reminders (user_id, case_id, remind_at, level) VALUES (?, ?, ?, ?)",
            (user_id, case_id, remind_10.isoformat(), 2),
        )
        await db.commit()


async def get_due_reminders() -> list[dict]:
    """Возвращает напоминания, время которых уже наступило."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM reminders WHERE remind_at <= ? AND sent = 0",
            (now,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_reminder_sent(reminder_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        await db.commit()


# ── Получение кейса по ID ────────────────────────────────────────────────

async def get_case_by_id(case_id: int) -> dict | None:
    """Возвращает анонимные данные кейса (без персональных полей)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id, user_id, triage_level, city, bully_age_group,
                      prior_actions, created_at
               FROM cases WHERE id = ?""",
            (case_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# ── История обращений ─────────────────────────────────────────────────────

async def get_user_cases(user_id: int) -> list[dict]:
    """Возвращает последние 5 обращений — только анонимные данные."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id, triage_level, city, bully_age_group, prior_actions, created_at
               FROM cases WHERE user_id = ?
               ORDER BY created_at DESC LIMIT 5""",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
