from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import sqlite3, io
from pathlib import Path
from datetime import date
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
DB = ROOT / "attendance.db"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
app = Flask(__name__)
app.secret_key = "local-mini-project-secret-change-before-deployment"

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS students(
            student_id TEXT PRIMARY KEY, name TEXT NOT NULL, class_name TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL,
            attendance_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Present','Absent')),
            UNIQUE(student_id, attendance_date),
            FOREIGN KEY(student_id) REFERENCES students(student_id))""")

def summary_df():
    with db() as con:
        students = pd.read_sql_query("SELECT * FROM students ORDER BY name", con)
        records = pd.read_sql_query("SELECT student_id, attendance_date, status FROM attendance", con)
    cols = ["student_id","name","class_name","total_classes","present","absent","percentage"]
    if students.empty:
        return pd.DataFrame(columns=cols)
    if records.empty:
        students["total_classes"] = 0; students["present"] = 0
        students["absent"] = 0; students["percentage"] = 0.0
        return students[cols]
    records["present_n"] = (records.status == "Present").astype(int)
    records["absent_n"] = (records.status == "Absent").astype(int)
    agg = records.groupby("student_id", as_index=False).agg(
        total_classes=("status","count"), present=("present_n","sum"), absent=("absent_n","sum"))
    df = students.merge(agg, on="student_id", how="left").fillna(0)
    df["percentage"] = df.apply(lambda r: round(100*r.present/r.total_classes, 2) if r.total_classes else 0.0, axis=1)
    for c in ["total_classes","present","absent"]: df[c] = df[c].astype(int)
    return df[cols]

@app.route("/")
def index():
    df = summary_df()
    with db() as con:
        student_count = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        record_count = con.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    avg = round(df.percentage.mean(), 2) if not df.empty else 0
    low = int((df.percentage < 75).sum()) if not df.empty else 0
    return render_template("index.html", summary=df.to_dict("records"), student_count=student_count,
                           record_count=record_count, avg=avg, low=low)

@app.route("/students", methods=["GET","POST"])
def students():
    if request.method == "POST":
        sid, name, cls = (request.form.get(k,"").strip() for k in ("student_id","name","class_name"))
        if not all((sid,name,cls)):
            flash("All fields are required.", "error")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO students VALUES (?,?,?)", (sid,name,cls))
                flash("Student added.", "success")
            except sqlite3.IntegrityError:
                flash("Student ID already exists.", "error")
        return redirect(url_for("students"))
    with db() as con: rows = con.execute("SELECT * FROM students ORDER BY name").fetchall()
    return render_template("students.html", students=rows)

@app.route("/attendance", methods=["GET","POST"])
def attendance():
    if request.method == "POST":
        day, sid, status = (request.form.get(k,"").strip() for k in ("attendance_date","student_id","status"))
        if not day or not sid or status not in ("Present","Absent"):
            flash("Select a date, student, and status.", "error")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO attendance(student_id,attendance_date,status) VALUES (?,?,?)", (sid,day,status))
                flash("Attendance saved.", "success")
            except sqlite3.IntegrityError:
                flash("Attendance already exists for this student on that date.", "error")
        return redirect(url_for("attendance"))
    with db() as con:
        students = con.execute("SELECT * FROM students ORDER BY name").fetchall()
        records = con.execute("""SELECT a.attendance_date,s.student_id,s.name,s.class_name,a.status
          FROM attendance a JOIN students s USING(student_id)
          ORDER BY a.attendance_date DESC,s.name LIMIT 300""").fetchall()
    return render_template("attendance.html", students=students, records=records, today=date.today().isoformat())

@app.route("/reports")
def reports():
    df = summary_df()
    chart = REPORTS / "attendance_chart.png"
    if not df.empty:
        plot = df.sort_values("percentage")
        plt.figure(figsize=(10, max(4, len(plot)*0.35)))
        plt.barh(plot.name, plot.percentage)
        plt.xlabel("Attendance (%)"); plt.title("Student-wise Attendance Percentage"); plt.xlim(0,100)
        plt.tight_layout(); plt.savefig(chart, dpi=150); plt.close()
    else:
        if chart.exists(): chart.unlink()
    with db() as con:
        counts = {r["status"]:r["n"] for r in con.execute("SELECT status,COUNT(*) n FROM attendance GROUP BY status")}
    return render_template("reports.html", summary=df.to_dict("records"), chart_exists=chart.exists(),
                           present=counts.get("Present",0), absent=counts.get("Absent",0))

@app.route("/chart.png")
def chart():
    p = REPORTS / "attendance_chart.png"
    if not p.exists(): return "No chart yet. Add attendance first.", 404
    return send_file(p, mimetype="image/png")

@app.route("/export.csv")
def export_csv():
    output = io.BytesIO(summary_df().to_csv(index=False).encode("utf-8-sig"))
    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="attendance_summary.csv")

@app.route("/load-demo")
def load_demo():
    demo = [("STU001","Aarav Sharma","CSE-A"),("STU002","Diya Reddy","CSE-A"),
            ("STU003","Ishaan Kumar","CSE-A"),("STU004","Meera Nair","CSE-B"),
            ("STU005","Rohan Das","CSE-B")]
    with db() as con:
        for s in demo: con.execute("INSERT OR IGNORE INTO students VALUES (?,?,?)", s)
        for offset in range(1,8):
            day = date.fromordinal(date.today().toordinal()-offset).isoformat()
            for i,s in enumerate(demo):
                status = "Absent" if (i+offset)%4 == 0 else "Present"
                con.execute("INSERT OR IGNORE INTO attendance(student_id,attendance_date,status) VALUES (?,?,?)",(s[0],day,status))
    flash("Demo data loaded.", "success")
    return redirect(url_for("index"))

init_db()
if __name__ == "__main__":
    app.run(debug=True)
