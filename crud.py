"""Database operations. Works on plain dicts and always uses parameterised SQL."""
import sqlite3
from typing import Optional

FIELDS = ("name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date")


class DuplicateEmailError(Exception):
    pass


def _row(row: Optional[sqlite3.Row]) -> Optional[dict]:
    return dict(row) if row else None


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def create_student(conn: sqlite3.Connection, data: dict) -> dict:
    cols = ", ".join(FIELDS)
    marks = ", ".join("?" for _ in FIELDS)
    try:
        cur = conn.execute(
            f"INSERT INTO students ({cols}) VALUES ({marks})",
            [data.get(f) for f in FIELDS],
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if "email" in str(exc).lower():
            raise DuplicateEmailError(data.get("email")) from exc
        raise
    return get_student(conn, cur.lastrowid)


def get_student(conn: sqlite3.Connection, student_id: int) -> Optional[dict]:
    return _row(conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone())


def list_students(
    conn: sqlite3.Connection,
    name: Optional[str] = None,
    course: Optional[str] = None,
    born_after: Optional[str] = None,    # ISO date, exclusive
    born_before: Optional[str] = None,   # ISO date, exclusive
    skip: int = 0,
    limit: Optional[int] = 100,
) -> list[dict]:
    where, params = [], []
    if name:
        where.append("name LIKE ? ESCAPE '\\' COLLATE NOCASE")
        params.append(f"%{_escape_like(name)}%")
    if course:
        where.append("course LIKE ? ESCAPE '\\' COLLATE NOCASE")
        params.append(f"%{_escape_like(course)}%")
    if born_after:
        where.append("date_of_birth > ?")
        params.append(born_after)
    if born_before:
        where.append("date_of_birth < ?")
        params.append(born_before)
    sql = "SELECT * FROM students"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += [limit, skip]
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def count_students(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]


def update_student(conn: sqlite3.Connection, student_id: int, data: dict) -> Optional[dict]:
    """Write all FIELDS from `data` (callers pass the full merged record)."""
    if get_student(conn, student_id) is None:
        return None
    sets = ", ".join(f"{f} = ?" for f in FIELDS)
    try:
        conn.execute(
            f"UPDATE students SET {sets} WHERE id = ?",
            [data.get(f) for f in FIELDS] + [student_id],
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if "email" in str(exc).lower():
            raise DuplicateEmailError(data.get("email")) from exc
        raise
    return get_student(conn, student_id)


def delete_student(conn: sqlite3.Connection, student_id: int) -> bool:
    cur = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    return cur.rowcount > 0
