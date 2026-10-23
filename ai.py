"""Optional bonus: natural-language questions answered by a local Ollama model.

Safety design
-------------
* The model NEVER writes or runs SQL.
* Backend code decides what to fetch (using the fixed, parameterised queries in
  crud.py), builds a text context from the result, and asks the model only to
  phrase an answer based on that context.
* Counts are computed by SQL, not by the model, and are always put in the context.
"""
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date
from typing import Optional

from . import crud

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
MAX_RECORDS_IN_CONTEXT = 50

SYSTEM_PROMPT = (
    "You are an assistant for a student records system. Answer the user's question "
    "using ONLY the data under 'DATABASE CONTEXT'. If the context does not contain "
    "the answer, say you don't have that information. Do not invent students or "
    "numbers. Be concise and readable."
)

_BORN_RE = re.compile(r"\bborn\s+(after|before|in)\s+(?:the\s+year\s+)?(\d{4})\b", re.I)


class OllamaUnavailable(Exception):
    pass


def retrieve(conn, question: str) -> tuple[str, int]:
    """Choose which records to fetch for this question; return (context_text, n_records)."""
    q = question.lower()
    total = crud.count_students(conn)

    born_after = born_before = None
    filters: list[str] = []

    m = _BORN_RE.search(question)
    if m:
        kind, year = m.group(1).lower(), int(m.group(2))
        if kind == "after":        # year-based: born in a year later than `year`
            born_after = date(year, 12, 31).isoformat()
            filters.append(f"born after {year}")
        elif kind == "before":
            born_before = date(year, 1, 1).isoformat()
            filters.append(f"born before {year}")
        else:
            born_after = date(year - 1, 12, 31).isoformat()
            born_before = date(year + 1, 1, 1).isoformat()
            filters.append(f"born in {year}")

    # Course mentioned? Match against the courses that actually exist.
    course_filter = None
    for (c,) in conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL"):
        if c.lower() in q:
            course_filter = c
            filters.append(f"course = {c}")
            break

    # Student name mentioned?
    name_filter = None
    for (n,) in conn.execute("SELECT name FROM students"):
        if n.lower() in q:
            name_filter = n
            filters.append(f"name = {n}")
            break

    matched = crud.list_students(
        conn,
        name=name_filter,
        course=course_filter,
        born_after=born_after,
        born_before=born_before,
        limit=None,
    )

    lines = [f"Total students in database: {total}"]
    if filters:
        lines.append(f"Filters applied: {', '.join(filters)}")
        lines.append(f"Number of students matching the filters: {len(matched)}")
    shown = matched[:MAX_RECORDS_IN_CONTEXT]
    lines.append(f"Student records ({len(shown)} shown):")
    for s in shown:
        parts = [f"id={s['id']}", f"name={s['name']}", f"dob={s['date_of_birth']}"]
        for key in ("course", "enrollment_date"):
            if s.get(key):
                parts.append(f"{key}={s[key]}")
        lines.append("- " + ", ".join(parts))
    if len(matched) > len(shown):
        lines.append(f"(... {len(matched) - len(shown)} more records not shown)")
    # Deliberately NOT included: email, phone, address (not needed to answer; privacy).
    return "\n".join(lines), len(shown)


def ask_ollama(question: str, context: str, timeout: float = 120.0) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"DATABASE CONTEXT:\n{context}\n\nQUESTION: {question}"},
        ],
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:200]
        raise OllamaUnavailable(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise OllamaUnavailable(
            f"Cannot reach Ollama at {OLLAMA_URL}. Is it running (`ollama serve`) "
            f"and is the model pulled (`ollama pull {OLLAMA_MODEL}`)?"
        ) from exc
    return body.get("message", {}).get("content", "").strip()
