PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'STAFF'
);

CREATE TABLE IF NOT EXISTS courses (
    course_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name     TEXT NOT NULL,
    department      TEXT NOT NULL,
    total_seats     INTEGER NOT NULL CHECK (total_seats > 0),
    seats_available INTEGER NOT NULL CHECK (seats_available >= 0),
    fees            REAL NOT NULL CHECK (fees >= 0),
    CHECK (seats_available <= total_seats)
);

CREATE TABLE IF NOT EXISTS applicants (
    applicant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    dob          TEXT NOT NULL,
    gender       TEXT NOT NULL CHECK (gender IN ('M', 'F', 'O')),
    phone        TEXT NOT NULL,
    email        TEXT NOT NULL,
    cutoff_mark  REAL NOT NULL CHECK (cutoff_mark BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_id   INTEGER NOT NULL REFERENCES applicants(applicant_id),
    course_id      INTEGER NOT NULL REFERENCES courses(course_id),
    apply_date     TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'PENDING'
                   CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    UNIQUE (applicant_id, course_id)
);

CREATE TABLE IF NOT EXISTS admissions (
    admission_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL UNIQUE REFERENCES applications(application_id),
    admission_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fee_payments (
    payment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_id INTEGER NOT NULL REFERENCES admissions(admission_id),
    amount       REAL NOT NULL CHECK (amount > 0),
    payment_date TEXT NOT NULL,
    payment_mode TEXT NOT NULL
);
