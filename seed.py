"""Fill the database with DUMMY students for demos/testing. No real data."""
from app import crud
from app.database import connect, init_db

DUMMY = [
    ("Aarav Sharma",  "2004-05-17", "aarav.sharma@example.com", "+91 90000 00001", "Python Backend", "2024-07-01"),
    ("Diya Patel",    "2006-02-11", "diya.patel@example.com",   "+91 90000 00002", "Data Science",   "2024-07-01"),
    ("Rohan Gupta",   "2005-11-30", "rohan.gupta@example.com",  None,             "Python Backend", "2024-08-15"),
    ("Ananya Iyer",   "2007-08-09", "ananya.iyer@example.com",  "+91 90000 00004", "Web Development", "2025-01-10"),
    ("Kabir Singh",   "2003-12-25", None,                       "+91 90000 00005", "Data Science",   "2023-07-01"),
    ("Meera Nair",    "2005-03-03", "meera.nair@example.com",   "+91 90000 00006", "Web Development", "2024-01-20"),
    ("Vihaan Das",    "2006-09-14", "vihaan.das@example.com",   None,             "Python Backend", "2025-01-10"),
    ("Ishita Roy",    "2004-01-28", "ishita.roy@example.com",   "+91 90000 00008", "Data Science",   "2023-07-01"),
]

if __name__ == "__main__":
    init_db()
    conn = connect()
    if crud.count_students(conn):
        print("Database already has data; seed skipped.")
    else:
        for name, dob, email, phone, course, enrolled in DUMMY:
            crud.create_student(conn, dict(name=name, date_of_birth=dob, email=email,
                                           phone=phone, course=course, enrollment_date=enrolled))
        print(f"Inserted {len(DUMMY)} dummy students.")
