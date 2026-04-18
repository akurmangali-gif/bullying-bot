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
                applicant_name TEXT,
                child_name TEXT,
                child_class TEXT,
                school_name TEXT,
                city TEXT,
                bully_age_group TEXT,
                incident_dates TEXT,
                incident_description TEXT,
                witnesses TEXT,
                has_evidence TEXT,
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
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO cases (
                user_id, triage_level, applicant_name, child_name,
                child_class, school_name, city, bully_age_group,
                incident_dates, incident_description, witnesses,
                has_evidence, prior_actions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data.get("triage_level"),
            data.get("applicant_name"),
            data.get("child_name"),
            data.get("child_class"),
            data.get("school_name"),
            data.get("city"),
            data.get("bully_age_group"),
            data.get("incident_dates"),
            data.get("incident_description"),
            data.get("witnesses"),
            data.get("has_evidence"),
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
    """Возвращает данные кейса для регенерации документов."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM cases WHERE id = ?""",
            (case_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# ── История обращений ─────────────────────────────────────────────────────

async def get_user_cases(user_id: int) -> list[dict]:
    """Возвращает последние 5 обращений пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT id, triage_level, child_name, school_name, city,
                      applicant_name, child_class, bully_age_group,
                      incident_description, prior_actions, created_at
               FROM cases WHERE user_id = ?
               ORDER BY created_at DESC LIMIT 5""",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
