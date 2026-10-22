import os
import sqlite3
from datetime import date

from . import config
from .default_templates import DEFAULT_TEMPLATES
from .translit import normalize_apostrophes, search_key

_conn: sqlite3.Connection | None = None

DEFAULT_SETTINGS = {
    "lang": "uz_latn",
    "send_time": "09:00",
    "group_id": "",
    "group_title": "",
    "thread_id": "",
    "notify_admins": "1",
    "pin": "1",
    "pinned": "[]",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    birth_date TEXT NOT NULL,          -- YYYY-MM-DD
    gender TEXT NOT NULL,              -- M / F
    telegram TEXT NOT NULL DEFAULT '', -- @username (ixtiyoriy)
    search_key TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lang TEXT NOT NULL,
    gender TEXT NOT NULL,
    text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sent_log (
    employee_id INTEGER NOT NULL,
    day TEXT NOT NULL,
    PRIMARY KEY (employee_id, day)
);
"""


def conn() -> sqlite3.Connection:
    assert _conn is not None, "db.init() chaqirilmagan"
    return _conn


def init(path: str = config.DB_PATH) -> None:
    global _conn
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.executescript(SCHEMA)
    for k, v in DEFAULT_SETTINGS.items():
        _conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))
    if not _conn.execute("SELECT 1 FROM templates LIMIT 1").fetchone():
        for (lang, gender), texts in DEFAULT_TEMPLATES.items():
            _conn.executemany(
                "INSERT INTO templates(lang, gender, text) VALUES (?, ?, ?)",
                [(lang, gender, t) for t in texts],
            )
    _conn.commit()


# ---------- settings ----------

def get_setting(key: str) -> str:
    row = conn().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else DEFAULT_SETTINGS.get(key, "")


def set_setting(key: str, value: str) -> None:
    conn().execute(
        "INSERT INTO settings(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn().commit()


# ---------- admins ----------

def is_admin(user_id: int) -> bool:
    if user_id in config.SUPER_ADMINS:
        return True
    return conn().execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone() is not None


def list_admins() -> list[sqlite3.Row]:
    return conn().execute("SELECT * FROM admins ORDER BY added_at").fetchall()


def all_admin_ids() -> set[int]:
    return set(config.SUPER_ADMINS) | {r["user_id"] for r in list_admins()}


def add_admin(user_id: int, name: str = "") -> None:
    conn().execute(
        "INSERT INTO admins(user_id, name) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET name = excluded.name",
        (user_id, name),
    )
    conn().commit()


def remove_admin(user_id: int) -> None:
    conn().execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn().commit()


# ---------- employees ----------

def clean_name(raw: str) -> str:
    """'TILYAYEV AZAMAT NAIMOVICH' -> 'Tilyayev Azamat Naimovich'"""
    s = normalize_apostrophes(" ".join(raw.split()))
    words = []
    for w in s.split(" "):
        if w.lower() in ("oʻgʻli", "ugli", "o‘g‘li", "qizi", "kizi", "ўғли", "угли", "қизи", "кизи"):
            words.append(w.lower())
        else:
            words.append("-".join(p[:1].upper() + p[1:].lower() for p in w.split("-")))
    return " ".join(words)


def add_employee(full_name: str, birth_date: date, gender: str, telegram: str = "") -> int:
    name = clean_name(full_name)
    cur = conn().execute(
        "INSERT INTO employees(full_name, birth_date, gender, telegram, search_key) VALUES (?, ?, ?, ?, ?)",
        (name, birth_date.isoformat(), gender, telegram, search_key(name)),
    )
    conn().commit()
    return cur.lastrowid


def update_employee(emp_id: int, **fields) -> None:
    if "full_name" in fields:
        fields["full_name"] = clean_name(fields["full_name"])
        fields["search_key"] = search_key(fields["full_name"])
    if isinstance(fields.get("birth_date"), date):
        fields["birth_date"] = fields["birth_date"].isoformat()
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn().execute(f"UPDATE employees SET {cols} WHERE id = ?", (*fields.values(), emp_id))
    conn().commit()


def delete_employee(emp_id: int) -> None:
    conn().execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn().execute("DELETE FROM sent_log WHERE employee_id = ?", (emp_id,))
    conn().commit()


def get_employee(emp_id: int) -> sqlite3.Row | None:
    return conn().execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()


def count_employees() -> int:
    return conn().execute("SELECT COUNT(*) FROM employees").fetchone()[0]


def list_employees(offset: int = 0, limit: int | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM employees ORDER BY full_name COLLATE NOCASE"
    if limit is not None:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
    return conn().execute(sql).fetchall()


def search_employees(query: str, limit: int = 30) -> list[sqlite3.Row]:
    words = search_key(query).split()
    if not words:
        return []
    where = " AND ".join("search_key LIKE ?" for _ in words)
    return conn().execute(
        f"SELECT * FROM employees WHERE {where} ORDER BY full_name COLLATE NOCASE LIMIT ?",
        (*[f"%{w}%" for w in words], limit),
    ).fetchall()


def birthdays_on(day: date) -> list[sqlite3.Row]:
    md = [day.strftime("%m-%d")]
    # 29-fevralda tug‘ilganlar kabisa bo‘lmagan yilda 28-fevralda tabriklanadi
    if md[0] == "02-28" and not _is_leap(day.year):
        md.append("02-29")
    marks = ",".join("?" for _ in md)
    return conn().execute(
        f"SELECT * FROM employees WHERE substr(birth_date, 6, 5) IN ({marks}) ORDER BY full_name",
        md,
    ).fetchall()


def _is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def was_sent(emp_id: int, day: date) -> bool:
    return conn().execute(
        "SELECT 1 FROM sent_log WHERE employee_id = ? AND day = ?", (emp_id, day.isoformat())
    ).fetchone() is not None


def mark_sent(emp_id: int, day: date) -> None:
    conn().execute(
        "INSERT OR IGNORE INTO sent_log(employee_id, day) VALUES (?, ?)", (emp_id, day.isoformat())
    )
    conn().commit()


# ---------- templates ----------

def list_templates(lang: str, gender: str) -> list[sqlite3.Row]:
    return conn().execute(
        "SELECT * FROM templates WHERE lang = ? AND gender = ? ORDER BY id", (lang, gender)
    ).fetchall()


def count_templates(lang: str, gender: str) -> int:
    return conn().execute(
        "SELECT COUNT(*) FROM templates WHERE lang = ? AND gender = ?", (lang, gender)
    ).fetchone()[0]


def get_template(tpl_id: int) -> sqlite3.Row | None:
    return conn().execute("SELECT * FROM templates WHERE id = ?", (tpl_id,)).fetchone()


def add_template(lang: str, gender: str, text: str) -> int:
    cur = conn().execute(
        "INSERT INTO templates(lang, gender, text) VALUES (?, ?, ?)", (lang, gender, text)
    )
    conn().commit()
    return cur.lastrowid


def update_template(tpl_id: int, text: str) -> None:
    conn().execute("UPDATE templates SET text = ? WHERE id = ?", (text, tpl_id))
    conn().commit()


def delete_template(tpl_id: int) -> None:
    conn().execute("DELETE FROM templates WHERE id = ?", (tpl_id,))
    conn().commit()
