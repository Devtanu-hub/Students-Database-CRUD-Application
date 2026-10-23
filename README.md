# Students Database CRUD API (FastAPI + SQLite + optional Ollama AI)

Backend internship project for **EWB Edu Tech Pvt. Ltd.** A Python REST API that manages
student records with full **C**reate / **R**ead / **U**pdate / **D**elete operations,
persistent SQLite storage, input validation, and an optional local-AI endpoint that
answers natural-language questions about the data.

## Features

- FastAPI REST API with automatic interactive docs (`/docs`)
- SQLite persistence (`students.db`, created automatically)
- Validation: required fields, email/phone format, DOB not in the future, unique email,
  at least one contact method, enrollment date not before birth date
- Proper errors: `404` missing record, `409` duplicate email, `422` invalid input
- Filtering and pagination on the list endpoint
- Parameterised SQL everywhere (no SQL injection)
- **Optional bonus:** `/ask` endpoint using a local Ollama model, grounded in retrieved records
- Automated tests (`pytest`) and a dummy-data seed script

## Project structure

```
app/
  main.py       API routes
  schemas.py    Pydantic models + validation rules
  crud.py       Database operations (plain SQL, parameterised)
  database.py   SQLite connection + schema
  ai.py         Optional Ollama integration
tests/          pytest API tests + stdlib DB tests
seed.py         Inserts 8 DUMMY students
requirements.txt
```

## Prerequisites

- Python 3.10+
- (Optional, for AI bonus) [Ollama](https://ollama.com) installed

## Installation

```bash
git clone <your-repo-url>
cd student-crud
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python seed.py                    # optional: load dummy data
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** for Swagger UI, where every endpoint can be tried in the browser.
The database file `students.db` is created on first start. Set `STUDENTS_DB=/path/to/file.db` to change its location.

## Student fields

| Field | Required | Notes |
|---|---|---|
| `id` | auto | Unique, generated |
| `name` | yes | 1-100 chars |
| `date_of_birth` | yes | `YYYY-MM-DD`, not in the future |
| `email` | one of email/phone | valid format, unique, stored lowercase |
| `phone` | one of email/phone | 7-20 chars: digits, `+ - ( )`, spaces |
| `course` | no | |
| `address` | no | |
| `enrollment_date` | no | `YYYY-MM-DD`, not before date of birth |

## API endpoints

| Method | Endpoint | Purpose | Success |
|---|---|---|---|
| POST | `/students` | Create a student | 201 |
| GET | `/students` | List / filter students | 200 |
| GET | `/students/{student_id}` | View one student | 200 |
| PUT | `/students/{student_id}` | Replace all details | 200 |
| PATCH | `/students/{student_id}` | Update only the fields sent | 200 |
| DELETE | `/students/{student_id}` | Delete a student | 204 |
| POST | `/ask` | *(Optional)* Ask AI about the data | 200 |

**List filters** (query parameters, combinable): `name`, `course` (partial, case-insensitive),
`born_after`, `born_before` (`YYYY-MM-DD`, exclusive), `skip`, `limit` (default 100, max 1000).

## Testing the API with curl

```bash
# Create
curl -X POST http://127.0.0.1:8000/students -H "Content-Type: application/json" \
  -d '{"name":"Aarav Sharma","date_of_birth":"2004-05-17","email":"aarav@example.com","phone":"+91 98765 43210","course":"Python Backend"}'

# List all / filter
curl http://127.0.0.1:8000/students
curl "http://127.0.0.1:8000/students?course=python&born_after=2004-12-31"

# View one
curl http://127.0.0.1:8000/students/1

# Partial update
curl -X PATCH http://127.0.0.1:8000/students/1 -H "Content-Type: application/json" \
  -d '{"course":"Data Science"}'

# Full replace
curl -X PUT http://127.0.0.1:8000/students/1 -H "Content-Type: application/json" \
  -d '{"name":"Aarav Sharma","date_of_birth":"2004-05-17","email":"aarav@example.com","course":"Web Development"}'

# Delete
curl -X DELETE http://127.0.0.1:8000/students/1

# Error handling examples
curl http://127.0.0.1:8000/students/999                                  # 404
curl -X POST http://127.0.0.1:8000/students -H "Content-Type: application/json" \
  -d '{"name":"X","date_of_birth":"2999-01-01","email":"bad"}'            # 422
```

## Automated tests

```bash
pytest -v                                     # full suite (API + database)
python -m unittest discover -s tests -t . -p "test_crud.py"   # DB layer only, no extra packages
```

## Optional bonus: local AI with Ollama

```bash
ollama pull llama3.2:1b
ollama serve                      # if not already running
uvicorn app.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"How many students are there?"}'

curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"List students born after 2005"}'
```

The response contains the `answer`, the `model`, how many `records_used`, and the exact
`context` that was given to the model, so every answer can be checked against the data.

Config via environment variables: `OLLAMA_URL` (default `http://localhost:11434`),
`OLLAMA_MODEL` (default `llama3.2:1b`). If Ollama is not running, `/ask` returns `503`
with a helpful message; the CRUD API is unaffected.

### How the AI stays safe and grounded

1. **The model never touches SQL.** Backend code interprets the question (count, "born
   after/before/in YEAR", course name, student name) and runs fixed, parameterised queries.
2. Retrieved records are placed in the prompt as context; the system prompt tells the model to answer
   **only** from that context and to say so when the data is missing.
3. Totals and match counts are computed by SQL and given to the model, so it does not have to count.
4. Only non-sensitive fields (id, name, DOB, course, enrollment date) are sent to the model; email, phone and
   address are never included. Temperature is 0 for consistent answers.
5. Context is capped at 50 records.

Note: "born after 2005" is interpreted as *born in a year later than 2005* (from 2006-01-01).
The question understanding is rule-based, so it handles the question styles above; unrecognised questions
fall back to the total count only, and the model will say if it cannot answer.

## Security & data notes

- Only **dummy data** is used (`seed.py`). Do not commit real student information.
- `*.db` files and `.env` are in `.gitignore`; no secrets are used or stored.
- All SQL uses bound parameters; `LIKE` wildcards in filters are escaped.
