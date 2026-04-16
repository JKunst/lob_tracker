import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "loopbaan.db"

TEACHER_PASSWORD = "mentor2024"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS students (
        leerlingnummer TEXT PRIMARY KEY,
        naam TEXT,
        mentorgroep TEXT,
        password_hash TEXT,
        password_set INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS task1 (
        leerlingnummer TEXT PRIMARY KEY,
        beoogd_beroep TEXT DEFAULT '',
        beoogde_opleiding TEXT DEFAULT '',
        stad TEXT DEFAULT '',
        open_dag INTEGER DEFAULT 0,
        meeloopdag INTEGER DEFAULT 0,
        ingeschreven INTEGER DEFAULT 0,
        updated_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS task2 (
        leerlingnummer TEXT PRIMARY KEY,
        beroepen TEXT DEFAULT '',
        opleidingen TEXT DEFAULT '',
        reflectie TEXT DEFAULT '',
        updated_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS task3 (
        leerlingnummer TEXT PRIMARY KEY,
        notities TEXT DEFAULT '',
        updated_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS task4 (
        leerlingnummer TEXT,
        interview_nr INTEGER,
        naam_persoon TEXT DEFAULT '',
        beroep TEXT DEFAULT '',
        relatie TEXT DEFAULT '',
        reflectie TEXT DEFAULT '',
        updated_at TEXT,
        PRIMARY KEY (leerlingnummer, interview_nr)
    )""")

    # Test student — wachtwoord: test123
    pw_hash = hash_password("test123")
    c.execute("""INSERT OR IGNORE INTO students (leerlingnummer, naam, mentorgroep, password_hash, password_set)
                 VALUES (?, ?, ?, ?, ?)""",
              ("999999", "Test Leerling", "4H1", pw_hash, 1))

    conn.commit()
    conn.close()


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def get_student(leerlingnummer):
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE leerlingnummer = ?", (leerlingnummer,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_login(leerlingnummer, password):
    student = get_student(leerlingnummer)
    if not student:
        return None
    if student["password_hash"] == hash_password(password):
        return student
    return None


def set_password(leerlingnummer, password):
    conn = get_conn()
    conn.execute(
        "UPDATE students SET password_hash = ?, password_set = 1 WHERE leerlingnummer = ?",
        (hash_password(password), leerlingnummer),
    )
    conn.commit()
    conn.close()


def add_student(leerlingnummer, naam, mentorgroep):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO students (leerlingnummer, naam, mentorgroep) VALUES (?, ?, ?)",
        (leerlingnummer, naam, mentorgroep),
    )
    conn.commit()
    conn.close()


def get_all_students():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM students ORDER BY mentorgroep, naam").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Task helpers ---

def get_task(table, leerlingnummer):
    conn = get_conn()
    row = conn.execute(f"SELECT * FROM {table} WHERE leerlingnummer = ?", (leerlingnummer,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def save_task1(leerlingnummer, data):
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO task1
           (leerlingnummer, beoogd_beroep, beoogde_opleiding, stad, open_dag, meeloopdag, ingeschreven, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            leerlingnummer,
            data["beoogd_beroep"],
            data["beoogde_opleiding"],
            data["stad"],
            int(data["open_dag"]),
            int(data["meeloopdag"]),
            int(data["ingeschreven"]),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def save_task2(leerlingnummer, data):
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO task2
           (leerlingnummer, beroepen, opleidingen, reflectie, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        (leerlingnummer, data["beroepen"], data["opleidingen"], data["reflectie"], datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def save_task3(leerlingnummer, data):
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO task3
           (leerlingnummer, notities, updated_at)
           VALUES (?, ?, ?)""",
        (leerlingnummer, data["notities"], datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_task4(leerlingnummer):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM task4 WHERE leerlingnummer = ? ORDER BY interview_nr", (leerlingnummer,)
    ).fetchall()
    conn.close()
    return {r["interview_nr"]: dict(r) for r in rows}


def save_task4_interview(leerlingnummer, nr, data):
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO task4
           (leerlingnummer, interview_nr, naam_persoon, beroep, relatie, reflectie, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            leerlingnummer,
            nr,
            data["naam_persoon"],
            data["beroep"],
            data["relatie"],
            data["reflectie"],
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def task_completion(leerlingnummer):
    """Returns dict of completion booleans per task."""
    t1 = get_task("task1", leerlingnummer)
    t2 = get_task("task2", leerlingnummer)
    t3 = get_task("task3", leerlingnummer)
    t4 = get_task4(leerlingnummer)

    interviews_done = len(
        [v for v in t4.values() if len(v.get("reflectie", "").split()) >= 300]
    )

    return {
        "task1": bool(t1.get("beoogd_beroep") or t1.get("beoogde_opleiding")),
        "task2": bool(t2.get("reflectie", "").strip()),
        "task3": bool(t3.get("notities", "").strip()),
        "task4": interviews_done >= 3,
    }
