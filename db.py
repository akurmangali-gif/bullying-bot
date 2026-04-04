import aiosqlite
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
