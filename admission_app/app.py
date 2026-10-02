"""College/University Admission Management System (Flask + SQLite)."""
import csv
import io
import os
import re
import sqlite3
from datetime import date
from functools import wraps
from secrets import token_hex

from flask import (Flask, Response, abort, flash, g, redirect,
                   render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("ADMISSION_DB", os.path.join(BASE_DIR, "admission.db"))
MIN_CUTOFF = 80.0          # minimum cutoff mark required for admission
PAYMENT_MODES = ["Cash", "UPI", "Card", "Net Banking", "Demand Draft"]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")


# ---------------------------------------------------------------- database
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        db.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'ADMIN')",
                   ("admin", generate_password_hash("admin123")))
    if db.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
        with open(os.path.join(BASE_DIR, "sample_data.sql"), encoding="utf-8") as f:
            db.executescript(f.read())
    db.commit()
    db.close()


def rows(sql, args=()):
    return get_db().execute(sql, args).fetchall()


def row(sql, args=()):
    return get_db().execute(sql, args).fetchone()


# ---------------------------------------------------------------- security
@app.before_request
def csrf_protect():
    if "csrf" not in session:
        session["csrf"] = token_hex(16)
    if request.method == "POST" and request.form.get("csrf") != session["csrf"]:
        abort(400)


app.jinja_env.globals["csrf_token"] = lambda: session.get("csrf", "")
app.jinja_env.filters["inr"] = lambda v: "₹{:,.0f}".format(v or 0)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = row("SELECT * FROM users WHERE username = ?", (request.form.get("username", "").strip(),))
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user"] = user["username"]
            session["csrf"] = token_hex(16)
            return redirect(url_for("dashboard"))
        flash("Username or password is incorrect.", "error")
    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- dashboard
@app.route("/")
@login_required
def dashboard():
    stats = row("""
        SELECT (SELECT COUNT(*) FROM applicants)                               AS applicants,
               (SELECT COUNT(*) FROM applications WHERE status = 'PENDING')    AS pending,
               (SELECT COUNT(*) FROM applications WHERE status = 'APPROVED')   AS approved,
               (SELECT COUNT(*) FROM applications WHERE status = 'REJECTED')   AS rejected,
               (SELECT COALESCE(SUM(amount), 0) FROM fee_payments)             AS collected""")
    seats = rows("SELECT course_name, department, total_seats, seats_available FROM courses ORDER BY course_id")
    return render_template("dashboard.html", stats=stats, seats=seats)


# ---------------------------------------------------------------- courses
def parse_course(form):
    errors, data = [], {}
    data["course_name"] = form.get("course_name", "").strip()
    data["department"] = form.get("department", "").strip()
    if not data["course_name"]:
        errors.append("Enter the course name.")
    if not data["department"]:
        errors.append("Enter the department.")
    try:
        data["total_seats"] = int(form.get("total_seats", ""))
        if data["total_seats"] < 1:
            raise ValueError
    except ValueError:
        errors.append("Total seats must be a whole number of 1 or more.")
    try:
        data["fees"] = float(form.get("fees", ""))
        if data["fees"] < 0:
            raise ValueError
    except ValueError:
        errors.append("Fees must be a number of 0 or more.")
    return data, errors


def render_courses(form=None):
    return render_template("courses.html", courses=rows("SELECT * FROM courses ORDER BY course_id"), form=form or {})


@app.route("/courses", methods=["GET", "POST"])
@login_required
def courses():
    if request.method == "POST":
        data, errors = parse_course(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_courses(request.form)
        get_db().execute(
            "INSERT INTO courses (course_name, department, total_seats, seats_available, fees) VALUES (?, ?, ?, ?, ?)",
            (data["course_name"], data["department"], data["total_seats"], data["total_seats"], data["fees"]))
        get_db().commit()
        flash(f"Added {data['course_name']}.", "ok")
        return redirect(url_for("courses"))
    return render_courses()


@app.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
def courses_edit(course_id):
    course = row("SELECT * FROM courses WHERE course_id = ?", (course_id,)) or abort(404)
    if request.method == "POST":
        data, errors = parse_course(request.form)
        if not errors:
            allotted = course["total_seats"] - course["seats_available"]
            if data["total_seats"] < allotted:
                errors.append(f"{allotted} seats are already allotted, so total seats cannot be lower than {allotted}.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("course_edit.html", course=course, form=request.form)
        available = data["total_seats"] - (course["total_seats"] - course["seats_available"])
        get_db().execute(
            "UPDATE courses SET course_name=?, department=?, total_seats=?, seats_available=?, fees=? WHERE course_id=?",
            (data["course_name"], data["department"], data["total_seats"], available, data["fees"], course_id))
        get_db().commit()
        flash("Course updated.", "ok")
        return redirect(url_for("courses"))
    return render_template("course_edit.html", course=course, form=course)


@app.post("/courses/<int:course_id>/delete")
@login_required
def courses_delete(course_id):
    try:
        get_db().execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
        get_db().commit()
        flash("Course deleted.", "ok")
    except sqlite3.IntegrityError:
        flash("This course has applications, so it cannot be deleted.", "error")
    return redirect(url_for("courses"))


# ---------------------------------------------------------------- applicants
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def parse_applicant(form):
    errors, data = [], {}
    data["name"] = form.get("name", "").strip()
    data["gender"] = form.get("gender", "")
    data["phone"] = form.get("phone", "").strip()
    data["email"] = form.get("email", "").strip()
    data["dob"] = form.get("dob", "")
    if not data["name"]:
        errors.append("Enter the applicant's name.")
    if data["gender"] not in ("M", "F", "O"):
        errors.append("Select a gender.")
    if not re.fullmatch(r"\d{10}", data["phone"]):
        errors.append("Phone number must be 10 digits.")
    if not EMAIL_RE.match(data["email"]):
        errors.append("Enter a valid email address.")
    try:
        if date.fromisoformat(data["dob"]) >= date.today():
            raise ValueError
    except ValueError:
        errors.append("Enter a valid date of birth in the past.")
    try:
        data["cutoff_mark"] = float(form.get("cutoff_mark", ""))
        if not 0 <= data["cutoff_mark"] <= 100:
            raise ValueError
    except ValueError:
        errors.append("Cutoff mark must be a number between 0 and 100.")
    return data, errors


def render_applicants(form=None):
    q = request.args.get("q", "").strip()
    like = f"%{q}%"
    items = rows("""SELECT * FROM applicants
                    WHERE name LIKE ? OR email LIKE ? OR phone LIKE ? OR CAST(applicant_id AS TEXT) = ?
                    ORDER BY applicant_id""", (like, like, like, q))
    return render_template("applicants.html", applicants=items, q=q, form=form or {})


@app.route("/applicants", methods=["GET", "POST"])
@login_required
def applicants():
    if request.method == "POST":
        data, errors = parse_applicant(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_applicants(request.form)
        get_db().execute(
            "INSERT INTO applicants (name, dob, gender, phone, email, cutoff_mark) VALUES (?, ?, ?, ?, ?, ?)",
            (data["name"], data["dob"], data["gender"], data["phone"], data["email"], data["cutoff_mark"]))
        get_db().commit()
        flash(f"Registered {data['name']}.", "ok")
        return redirect(url_for("applicants"))
    return render_applicants()


@app.route("/applicants/<int:applicant_id>/edit", methods=["GET", "POST"])
@login_required
def applicants_edit(applicant_id):
    person = row("SELECT * FROM applicants WHERE applicant_id = ?", (applicant_id,)) or abort(404)
    if request.method == "POST":
        data, errors = parse_applicant(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("applicant_edit.html", person=person, form=request.form)
        get_db().execute(
            "UPDATE applicants SET name=?, dob=?, gender=?, phone=?, email=?, cutoff_mark=? WHERE applicant_id=?",
            (data["name"], data["dob"], data["gender"], data["phone"], data["email"], data["cutoff_mark"], applicant_id))
        get_db().commit()
        flash("Applicant updated.", "ok")
        return redirect(url_for("applicants"))
    return render_template("applicant_edit.html", person=person, form=person)


@app.post("/applicants/<int:applicant_id>/delete")
@login_required
def applicants_delete(applicant_id):
    try:
        get_db().execute("DELETE FROM applicants WHERE applicant_id = ?", (applicant_id,))
        get_db().commit()
        flash("Applicant deleted.", "ok")
    except sqlite3.IntegrityError:
        flash("This applicant has applications, so the record cannot be deleted.", "error")
    return redirect(url_for("applicants"))


# ---------------------------------------------------------------- applications
@app.route("/applications", methods=["GET", "POST"])
@login_required
def applications():
    if request.method == "POST":
        try:
            applicant_id = int(request.form.get("applicant_id", ""))
            course_id = int(request.form.get("course_id", ""))
            get_db().execute(
                "INSERT INTO applications (applicant_id, course_id, apply_date) VALUES (?, ?, ?)",
                (applicant_id, course_id, date.today().isoformat()))
            get_db().commit()
            flash("Application submitted with status PENDING.", "ok")
        except ValueError:
            flash("Select an applicant and a course.", "error")
        except sqlite3.IntegrityError:
            flash("This applicant has already applied for that course.", "error")
        return redirect(url_for("applications"))
    status = request.args.get("status", "")
    sql = """SELECT ap.application_id, ap.apply_date, ap.status, a.name, a.cutoff_mark, c.course_name, c.department
             FROM applications ap
             JOIN applicants a ON a.applicant_id = ap.applicant_id
             JOIN courses c ON c.course_id = ap.course_id"""
    args = ()
    if status in ("PENDING", "APPROVED", "REJECTED"):
        sql += " WHERE ap.status = ?"
        args = (status,)
    items = rows(sql + " ORDER BY ap.application_id", args)
    return render_template("applications.html", items=items, status=status, min_cutoff=MIN_CUTOFF,
                           applicants=rows("SELECT applicant_id, name, cutoff_mark FROM applicants ORDER BY name"),
                           courses=rows("SELECT course_id, course_name, seats_available FROM courses ORDER BY course_name"))


def process_one(db, application_id):
    """Apply the admission rule to one pending application.
    Returns (status, message). Approved: cutoff >= MIN_CUTOFF and a seat is free."""
    r = db.execute("""SELECT ap.status, ap.course_id, a.name, a.cutoff_mark, c.course_name, c.seats_available
                      FROM applications ap
                      JOIN applicants a ON a.applicant_id = ap.applicant_id
                      JOIN courses c ON c.course_id = ap.course_id
                      WHERE ap.application_id = ?""", (application_id,)).fetchone()
    if r is None or r["status"] != "PENDING":
        return None, "Application is not pending."
    if r["cutoff_mark"] < MIN_CUTOFF:
        reason = f"cutoff {r['cutoff_mark']:g} is below the minimum of {MIN_CUTOFF:g}"
    elif r["seats_available"] <= 0:
        reason = f"no seats are left in {r['course_name']}"
    else:
        reason = None
    with db:
        if reason:
            db.execute("UPDATE applications SET status = 'REJECTED' WHERE application_id = ?", (application_id,))
            return "REJECTED", f"{r['name']} rejected: {reason}."
        db.execute("UPDATE applications SET status = 'APPROVED' WHERE application_id = ?", (application_id,))
        db.execute("UPDATE courses SET seats_available = seats_available - 1 WHERE course_id = ?", (r["course_id"],))
        db.execute("INSERT INTO admissions (application_id, admission_date) VALUES (?, ?)",
                   (application_id, date.today().isoformat()))
    return "APPROVED", f"{r['name']} admitted to {r['course_name']}."


@app.post("/applications/<int:application_id>/process")
@login_required
def applications_process(application_id):
    status, msg = process_one(get_db(), application_id)
    flash(msg, "ok" if status == "APPROVED" else "error")
    return redirect(url_for("applications"))


@app.post("/applications/process-all")
@login_required
def applications_process_all():
    """Merit-based allotment: highest cutoff first."""
    db = get_db()
    pending = db.execute("""SELECT ap.application_id FROM applications ap
                            JOIN applicants a ON a.applicant_id = ap.applicant_id
                            WHERE ap.status = 'PENDING'
                            ORDER BY a.cutoff_mark DESC, ap.application_id""").fetchall()
    approved = rejected = 0
    for p in pending:
        status, _ = process_one(db, p["application_id"])
        approved += status == "APPROVED"
        rejected += status == "REJECTED"
    flash(f"Processed {len(pending)} applications in merit order: {approved} approved, {rejected} rejected.", "ok")
    return redirect(url_for("applications"))


@app.post("/applications/<int:application_id>/delete")
@login_required
def applications_delete(application_id):
    db = get_db()
    r = db.execute("SELECT status FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    if r is None:
        abort(404)
    if r["status"] != "PENDING":
        flash("Only pending applications can be withdrawn.", "error")
    else:
        db.execute("DELETE FROM applications WHERE application_id = ?", (application_id,))
        db.commit()
        flash("Application withdrawn.", "ok")
    return redirect(url_for("applications"))


# ---------------------------------------------------------------- admissions & fees
ADMISSION_SQL = """
    SELECT ad.admission_id, ad.admission_date, a.name, c.course_name, c.department, c.fees,
           COALESCE(SUM(fp.amount), 0) AS paid, c.fees - COALESCE(SUM(fp.amount), 0) AS balance
    FROM admissions ad
    JOIN applications ap ON ap.application_id = ad.application_id
    JOIN applicants a ON a.applicant_id = ap.applicant_id
    JOIN courses c ON c.course_id = ap.course_id
    LEFT JOIN fee_payments fp ON fp.admission_id = ad.admission_id
    GROUP BY ad.admission_id
    ORDER BY ad.admission_id"""


@app.route("/admissions")
@login_required
def admissions():
    return render_template("admissions.html", items=rows(ADMISSION_SQL))


@app.route("/fees", methods=["GET", "POST"])
@login_required
def fees():
    if request.method == "POST":
        try:
            admission_id = int(request.form.get("admission_id", ""))
            amount = float(request.form.get("amount", ""))
            mode = request.form.get("payment_mode", "")
            if amount <= 0 or mode not in PAYMENT_MODES:
                raise ValueError
        except ValueError:
            flash("Select an admission, enter an amount above 0, and choose a payment mode.", "error")
            return redirect(url_for("fees"))
        adm = next((a for a in rows(ADMISSION_SQL) if a["admission_id"] == admission_id), None)
        if adm is None:
            abort(404)
        if amount > adm["balance"]:
            flash(f"{adm['name']} owes {adm['balance']:,.0f}. The payment cannot be more than the balance.", "error")
        else:
            get_db().execute(
                "INSERT INTO fee_payments (admission_id, amount, payment_date, payment_mode) VALUES (?, ?, ?, ?)",
                (admission_id, amount, date.today().isoformat(), mode))
            get_db().commit()
            flash(f"Recorded {amount:,.0f} from {adm['name']}.", "ok")
        return redirect(url_for("fees"))
    payments = rows("""SELECT fp.payment_id, fp.payment_date, fp.amount, fp.payment_mode, a.name, c.course_name
                       FROM fee_payments fp
                       JOIN admissions ad ON ad.admission_id = fp.admission_id
                       JOIN applications ap ON ap.application_id = ad.application_id
                       JOIN applicants a ON a.applicant_id = ap.applicant_id
                       JOIN courses c ON c.course_id = ap.course_id
                       ORDER BY fp.payment_id DESC""")
    due = [a for a in rows(ADMISSION_SQL) if a["balance"] > 0]
    return render_template("fees.html", payments=payments, due=due, modes=PAYMENT_MODES)


# ---------------------------------------------------------------- reports
REPORTS = {
    "application-status": ("Application status", """
        SELECT ap.application_id AS "Application", a.name AS "Applicant", c.course_name AS "Course",
               a.cutoff_mark AS "Cutoff", ap.apply_date AS "Applied on", ap.status AS "Status"
        FROM applications ap
        JOIN applicants a ON a.applicant_id = ap.applicant_id
        JOIN courses c ON c.course_id = ap.course_id
        ORDER BY ap.application_id"""),
    "admission-list": ("Admission list", """
        SELECT ad.admission_id AS "Admission", a.name AS "Student", c.course_name AS "Course",
               c.department AS "Dept", ad.admission_date AS "Admitted on"
        FROM admissions ad
        JOIN applications ap ON ap.application_id = ad.application_id
        JOIN applicants a ON a.applicant_id = ap.applicant_id
        JOIN courses c ON c.course_id = ap.course_id
        ORDER BY c.course_name, a.name"""),
    "seat-availability": ("Seat availability", """
        SELECT course_name AS "Course", department AS "Dept", total_seats AS "Total seats",
               total_seats - seats_available AS "Allotted", seats_available AS "Available"
        FROM courses ORDER BY course_id"""),
    "fee-collection": ("Fee collection", """
        SELECT c.course_name AS "Course", COUNT(DISTINCT ad.admission_id) AS "Students",
               COUNT(DISTINCT ad.admission_id) * c.fees AS "Fees due",
               COALESCE(SUM(fp.amount), 0) AS "Collected"
        FROM courses c
        LEFT JOIN applications ap ON ap.course_id = c.course_id
        LEFT JOIN admissions ad ON ad.application_id = ap.application_id
        LEFT JOIN fee_payments fp ON fp.admission_id = ad.admission_id
        GROUP BY c.course_id ORDER BY c.course_id"""),
}


@app.route("/reports")
@login_required
def reports():
    data = [(key, title, rows(sql)) for key, (title, sql) in REPORTS.items()]
    return render_template("reports.html", data=data)


@app.route("/reports/<name>.csv")
@login_required
def reports_csv(name):
    if name not in REPORTS:
        abort(404)
    title, sql = REPORTS[name]
    cur = get_db().execute(sql)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([d[0] for d in cur.description])
    writer.writerows(cur.fetchall())
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={name}.csv"})


if __name__ == "__main__":
    init_db()
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
