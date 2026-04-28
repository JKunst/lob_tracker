"""
db.py — SQLite helpers voor de LOB-app.

Primaire sleutel: ECK-iD (via portaal-token).
Geen wachtwoorden, geen leerlingnummers opgeslagen.
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_PATH = os.environ.get("LOB_DB_PATH", "loopbaan.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            eckid       TEXT PRIMARY KEY,
            naam        TEXT,
            mentorgroep TEXT
        );

        CREATE TABLE IF NOT EXISTS task1 (
            eckid             TEXT PRIMARY KEY,
            beoogd_beroep     TEXT DEFAULT '',
            beoogde_opleiding TEXT DEFAULT '',
            stad              TEXT DEFAULT '',
            open_dag          INTEGER DEFAULT 0,
            meeloopdag        INTEGER DEFAULT 0,
            ingeschreven      INTEGER DEFAULT 0,
            updated_at        TEXT
        );

        CREATE TABLE IF NOT EXISTS task2 (
            eckid       TEXT PRIMARY KEY,
            beroepen    TEXT DEFAULT '',
            opleidingen TEXT DEFAULT '',
            reflectie   TEXT DEFAULT '',
            updated_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS task3 (
            eckid      TEXT PRIMARY KEY,
            notities   TEXT DEFAULT '',
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS task4 (
            eckid        TEXT,
            interview_nr INTEGER,
            naam_persoon TEXT DEFAULT '',
            beroep       TEXT DEFAULT '',
            relatie      TEXT DEFAULT '',
            reflectie    TEXT DEFAULT '',
            updated_at   TEXT,
            PRIMARY KEY (eckid, interview_nr)
        );
    """)

    conn.commit()
    conn.close()


# ── SSO-login ─────────────────────────────────────────────────────────────────

def sso_upsert_student(eckid: str, naam: str, klas: str = None) -> dict:
    """Sla leerling op na SSO-login. Maakt aan als nieuw, updatet naam/klas."""
    conn = get_conn()
    conn.execute("""
        INSERT INTO students (eckid, naam, mentorgroep)
        VALUES (?, ?, ?)
        ON CONFLICT(eckid) DO UPDATE SET
            naam        = excluded.naam,
            mentorgroep = excluded.mentorgroep
    """, (eckid, naam, klas or "—"))
    conn.commit()
    row = conn.execute("SELECT * FROM students WHERE eckid = ?", (eckid,)).fetchone()
    conn.close()
    return dict(row)


def get_student(eckid: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE eckid = ?", (eckid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_students() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM students ORDER BY mentorgroep, naam").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Task helpers ──────────────────────────────────────────────────────────────

def get_task(table: str, eckid: str) -> dict:
    conn = get_conn()
    row = conn.execute(f"SELECT * FROM {table} WHERE eckid = ?", (eckid,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def save_task1(eckid: str, data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO task1
            (eckid, beoogd_beroep, beoogde_opleiding, stad, open_dag, meeloopdag, ingeschreven, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        eckid,
        data["beoogd_beroep"], data["beoogde_opleiding"], data["stad"],
        int(data["open_dag"]), int(data["meeloopdag"]), int(data["ingeschreven"]),
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def save_task2(eckid: str, data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO task2
            (eckid, beroepen, opleidingen, reflectie, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (eckid, data["beroepen"], data["opleidingen"], data["reflectie"], datetime.now().isoformat()))
    conn.commit()
    conn.close()


def save_task3(eckid: str, data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO task3 (eckid, notities, updated_at)
        VALUES (?, ?, ?)
    """, (eckid, data["notities"], datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_task4(eckid: str) -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM task4 WHERE eckid = ? ORDER BY interview_nr", (eckid,)
    ).fetchall()
    conn.close()
    return {r["interview_nr"]: dict(r) for r in rows}


def save_task4_interview(eckid: str, nr: int, data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO task4
            (eckid, interview_nr, naam_persoon, beroep, relatie, reflectie, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        eckid, nr,
        data["naam_persoon"], data["beroep"], data["relatie"], data["reflectie"],
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def task_completion(eckid: str) -> dict[str, bool]:
    t1 = get_task("task1", eckid)
    t2 = get_task("task2", eckid)
    t3 = get_task("task3", eckid)
    t4 = get_task4(eckid)
    interviews_done = sum(
        1 for v in t4.values() if len(v.get("reflectie", "").split()) >= 300
    )
    return {
        "task1": bool(t1.get("beoogd_beroep") or t1.get("beoogde_opleiding")),
        "task2": bool(t2.get("reflectie", "").strip()),
        "task3": bool(t3.get("notities", "").strip()),
        "task4": interviews_done >= 3,
    }
