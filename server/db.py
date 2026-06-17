import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from server.models import Resume, JobDescription, JobSkillRequirement, HRReview

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"


def _db() -> Path:
    DB_PATH.parent.mkdir(exist_ok=True)
    return DB_PATH


def init_db():
    with sqlite3.connect(_db()) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                name TEXT,
                phone TEXT,
                email TEXT,
                education TEXT,
                years_of_experience INTEGER DEFAULT 0,
                skills_json TEXT NOT NULL DEFAULT '[]',
                companies_json TEXT NOT NULL DEFAULT '[]',
                raw_text TEXT NOT NULL DEFAULT '',
                confidence REAL DEFAULT 0,
                parse_error TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                department TEXT,
                description TEXT NOT NULL DEFAULT '',
                required_education TEXT,
                min_years_experience INTEGER DEFAULT 0,
                skills_json TEXT NOT NULL DEFAULT '[]',
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                resume_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                note TEXT NOT NULL DEFAULT '',
                interview_advice TEXT NOT NULL DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(job_id, resume_id)
            )
        """)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(_db())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _resume_from_row(row: sqlite3.Row) -> Resume:
    return Resume(
        id=row["id"],
        filename=row["filename"],
        name=row["name"],
        phone=row["phone"],
        email=row["email"],
        education=row["education"],
        years_of_experience=row["years_of_experience"] or 0,
        skills=json.loads(row["skills_json"] or "[]"),
        recent_companies=json.loads(row["companies_json"] or "[]"),
        raw_text=row["raw_text"] or "",
        confidence=row["confidence"] or 0,
        parse_error=row["parse_error"],
        created_at=row["created_at"],
    )


def _jd_from_row(row: sqlite3.Row) -> JobDescription:
    return JobDescription(
        id=row["id"],
        title=row["title"],
        department=row["department"],
        description=row["description"] or "",
        required_education=row["required_education"],
        min_years_experience=row["min_years_experience"] or 0,
        skills=[JobSkillRequirement(**s) for s in json.loads(row["skills_json"] or "[]")],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def save_resume(r: Resume) -> Resume:
    with get_conn() as conn:
        c = conn.cursor()
        if r.id is not None:
            c.execute(
                "UPDATE resumes SET filename=?, name=?, phone=?, email=?, education=?, "
                "years_of_experience=?, skills_json=?, companies_json=?, raw_text=?, "
                "confidence=?, parse_error=? WHERE id=?",
                (r.filename, r.name, r.phone, r.email, r.education, r.years_of_experience,
                 json.dumps([s.model_dump() for s in r.skills], ensure_ascii=False),
                 json.dumps([e.model_dump() for e in r.recent_companies], ensure_ascii=False),
                 r.raw_text, r.confidence, r.parse_error, r.id),
            )
        else:
            c.execute(
                "INSERT INTO resumes (filename, name, phone, email, education, years_of_experience, "
                "skills_json, companies_json, raw_text, confidence, parse_error) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r.filename, r.name, r.phone, r.email, r.education, r.years_of_experience,
                 json.dumps([s.model_dump() for s in r.skills], ensure_ascii=False),
                 json.dumps([e.model_dump() for e in r.recent_companies], ensure_ascii=False),
                 r.raw_text, r.confidence, r.parse_error),
            )
            r.id = c.lastrowid
    return r


def get_resume(resume_id: int) -> Optional[Resume]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
        return _resume_from_row(row) if row else None


def list_resumes() -> List[Resume]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM resumes ORDER BY id DESC").fetchall()
        return [_resume_from_row(r) for r in rows]


def save_job(jd: JobDescription) -> JobDescription:
    with get_conn() as conn:
        c = conn.cursor()
        skills_json = json.dumps([s.model_dump() for s in jd.skills], ensure_ascii=False)
        if jd.id is not None:
            c.execute(
                "UPDATE jobs SET title=?, department=?, description=?, required_education=?, "
                "min_years_experience=?, skills_json=?, is_active=?, updated_at=datetime('now') WHERE id=?",
                (jd.title, jd.department, jd.description, jd.required_education,
                 jd.min_years_experience, skills_json, 1 if jd.is_active else 0, jd.id),
            )
        else:
            c.execute(
                "INSERT INTO jobs (title, department, description, required_education, "
                "min_years_experience, skills_json, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (jd.title, jd.department, jd.description, jd.required_education,
                 jd.min_years_experience, skills_json, 1 if jd.is_active else 0),
            )
            jd.id = c.lastrowid
    return jd


def get_job(job_id: int) -> Optional[JobDescription]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return _jd_from_row(row) if row else None


def list_jobs(active_only: bool = False) -> List[JobDescription]:
    query = "SELECT * FROM jobs"
    if active_only:
        query += " WHERE is_active=1"
    query += " ORDER BY id DESC"
    with get_conn() as conn:
        rows = conn.execute(query).fetchall()
        return [_jd_from_row(r) for r in rows]


def delete_job(job_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        return cur.rowcount > 0


def _review_from_row(row: sqlite3.Row) -> HRReview:
    return HRReview(
        id=row["id"],
        job_id=row["job_id"],
        resume_id=row["resume_id"],
        status=row["status"] or "pending",
        note=row["note"] or "",
        interview_advice=row["interview_advice"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def get_review(job_id: int, resume_id: int) -> Optional[HRReview]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM reviews WHERE job_id=? AND resume_id=?",
            (job_id, resume_id),
        ).fetchone()
        return _review_from_row(row) if row else None


def list_reviews_by_job(job_id: int) -> Dict[int, HRReview]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM reviews WHERE job_id=?", (job_id,)).fetchall()
        return {r["resume_id"]: _review_from_row(r) for r in rows}


def save_review(rev: HRReview) -> HRReview:
    with get_conn() as conn:
        c = conn.cursor()
        existing = conn.execute(
            "SELECT id FROM reviews WHERE job_id=? AND resume_id=?",
            (rev.job_id, rev.resume_id),
        ).fetchone()
        if existing:
            c.execute(
                "UPDATE reviews SET status=?, note=?, interview_advice=?, updated_at=datetime('now') WHERE id=?",
                (rev.status, rev.note, rev.interview_advice, existing["id"]),
            )
            rev.id = existing["id"]
        else:
            c.execute(
                "INSERT INTO reviews (job_id, resume_id, status, note, interview_advice) VALUES (?, ?, ?, ?, ?)",
                (rev.job_id, rev.resume_id, rev.status, rev.note, rev.interview_advice),
            )
            rev.id = c.lastrowid
    return rev


init_db()
