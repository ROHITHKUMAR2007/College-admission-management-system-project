# College/University Admission Management System

A DBMS mini project built with Python, Flask and SQLite.

## Run it

```
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 and sign in with **admin / admin123**.
The database file `admission.db` and sample data are created automatically on first run.
To start fresh, stop the app, delete `admission.db`, and run it again.

## Modules

| Module | Page |
| --- | --- |
| User Login | /login |
| Applicant Registration | /applicants |
| Course & Seat Management | /courses |
| Application & Admission Processing | /applications, /admissions |
| Fee Management | /fees |
| Reports (with CSV download) | /reports |

## Admission rule

An application is **approved** when the applicant's cutoff mark is at least 80 and a seat is free
in the course. Approval reduces the seat count by one and creates an admission record.
Otherwise it is **rejected**. "Process all pending by merit" works through pending applications
from the highest cutoff to the lowest. Change `MIN_CUTOFF` in `app.py` to use a different limit.

## Files

- `app.py` – routes and business logic
- `schema.sql` – tables (users, courses, applicants, applications, admissions, fee_payments)
- `sample_data.sql` – sample courses, applicants and applications
- `templates/`, `static/style.css` – pages and styling
