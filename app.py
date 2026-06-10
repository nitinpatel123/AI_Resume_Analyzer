from flask import Flask, render_template, request, send_file, redirect, session, flash
import matplotlib.pyplot as plt
import os
import pdfplumber
import sqlite3
import re

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey123"

UPLOAD_FOLDER = "uploads"
REPORT_FOLDER = "reports"
STATIC_FOLDER = "static"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect("resumes.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS resumes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            ats_score INTEGER,
            resume_score INTEGER,
            level TEXT,
            role TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- SAVE TO DB ----------------

def save_to_db(filename, ats, resume, level, role):
    conn = sqlite3.connect("resumes.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO resumes
        (filename, ats_score, resume_score, level, role)
        VALUES(?,?,?,?,?)
    """, (filename, ats, resume, level, role))

    conn.commit()
    conn.close()

# ---------------- SKILLS ----------------

SKILLS = [
    "python","java","c++","sql","html","css",
    "javascript","flask","django",
    "machine learning","data science",
    "excel","power bi","numpy","pandas",
    "git","github","react","docker","aws"
]

# ---------------- PDF TEXT ----------------

def extract_text(path):
    text = ""

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    return text.lower()

# ---------------- CLEAN TEXT ----------------

def clean_text(text):
    return re.sub(r'[^a-zA-Z ]', ' ', text.lower())

# ---------------- ANALYSIS ----------------

def analyze(text):

    matched = [s for s in SKILLS if s in text]
    missing = [s for s in SKILLS if s not in text]

    ats = int((len(matched) / len(SKILLS)) * 100)

    resume_score = ats

    if len(matched) > 5:
        resume_score += 10

    resume_score = min(resume_score, 100)

    level = (
        "🔥 Excellent"
        if resume_score >= 80
        else "👍 Good"
        if resume_score >= 50
        else "⚠️ Weak"
    )

    if "machine learning" in text:
        role = "ML Engineer"

    elif "flask" in text or "django" in text:
        role = "Backend Developer"

    elif "html" in text and "css" in text:
        role = "Frontend Developer"

    elif "react" in text:
        role = "Full Stack Developer"

    else:
        role = "Software Developer"

    feedback = []

    if "python" not in text:
        feedback.append("Add Python skill")

    if "sql" not in text:
        feedback.append("Add SQL skill")

    if "git" not in text:
        feedback.append("Add Git/GitHub")

    if "project" not in text:
        feedback.append("Add Projects section")

    if "aws" not in text:
        feedback.append("Add AWS / Cloud skills")

    return (
        ats,
        resume_score,
        matched,
        missing,
        level,
        role,
        feedback
    )

# ---------------- GRAPH ----------------

def create_graph(ats, resume):

    plt.figure(figsize=(5,4))

    plt.bar(
        ["ATS Score", "Resume Score"],
        [ats, resume],
        color=["blue", "green"]
    )

    plt.ylim(0, 100)

    graph_path = os.path.join(
        STATIC_FOLDER,
        "graph.png"
    )

    plt.savefig(graph_path)
    plt.close()

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = generate_password_hash(
            request.form["password"]
        )

        conn = sqlite3.connect("resumes.db")
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (username, password)
            )

            conn.commit()

            flash("Registration Successful")

            return redirect("/login")

        except:
            return "User Already Exists"

        finally:
            conn.close()

    return render_template("register.html")

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("resumes.db")
        c = conn.cursor()

        c.execute(
            "SELECT password FROM users WHERE username=?",
            (username,)
        )

        user = c.fetchone()

        conn.close()

        if user and check_password_hash(
            user[0],
            password
        ):

            session["user"] = username

            return redirect("/")

        return "Invalid Credentials"

    return render_template("login.html")

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")
# ---------------- HOME ----------------

@app.route("/", methods=["GET", "POST"])
def home():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        file = request.files["resume"]

        if file.filename == "":
            return "No file selected"

        path = os.path.join(
            UPLOAD_FOLDER,
            file.filename
        )

        file.save(path)

        text = extract_text(path)

        (
            ats,
            resume_score,
            matched,
            missing,
            level,
            role,
            feedback
        ) = analyze(text)

        create_graph(
            ats,
            resume_score
        )

        save_to_db(
            file.filename,
            ats,
            resume_score,
            level,
            role
        )

        suggestions = (
            "Add more projects, certifications, GitHub profile and cloud skills to improve your resume."
        )

        return render_template(
            "result.html",
            ats_score=ats,
            resume_score=resume_score,
            ai_score=resume_score,
            matched=matched,
            missing=missing,
            missing_skills=[],
match_score=round((ats + resume_score) / 2, 2),
            suggestions=suggestions,
            level=level,
            role=role,
            feedback=feedback
        )

    return render_template(
        "index.html",
        user=session["user"]
    )

# ---------------- HISTORY ----------------

@app.route("/history")
def history():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("resumes.db")
    c = conn.cursor()

    c.execute(
        "SELECT * FROM resumes ORDER BY id DESC"
    )

    data = c.fetchall()

    conn.close()

    return render_template(
        "history.html",
        data=data
    )

# ---------------- COMPARE ----------------

@app.route("/compare", methods=["POST"])
def compare():

    file1 = request.files["resume1"]
    file2 = request.files["resume2"]

    path1 = os.path.join(
        UPLOAD_FOLDER,
        file1.filename
    )

    path2 = os.path.join(
        UPLOAD_FOLDER,
        file2.filename
    )

    file1.save(path1)
    file2.save(path2)

    text1 = extract_text(path1)
    text2 = extract_text(path2)

    (
        score1,
        ai1,
        matched1,
        missing1,
        level1,
        role1,
        feedback1
    ) = analyze(text1)

    (
        score2,
        ai2,
        matched2,
        missing2,
        level2,
        role2,
        feedback2
    ) = analyze(text2)

    winner = (
        file1.filename
        if ai1 > ai2
        else file2.filename
        if ai2 > ai1
        else "Tie"
    )

    return render_template(
        "compare.html",
        file1=file1.filename,
        file2=file2.filename,
        score1=score1,
        score2=score2,
        ai_score1=ai1,
        ai_score2=ai2,
        matched1=matched1,
        matched2=matched2,
        winner=winner
    )

# ---------------- RESUME JOB MATCH ----------------

@app.route("/match", methods=["POST"])
def match():

    resume_text = request.form[
        "resume_text"
    ].lower()

    job_description = request.form[
        "job_description"
    ].lower()

    resume_skills = [
        s for s in SKILLS
        if s in resume_text
    ]

    job_skills = [
        s for s in SKILLS
        if s in job_description
    ]

    matched_skills = list(
        set(resume_skills)
        &
        set(job_skills)
    )

    missing_skills = list(
        set(job_skills)
        -
        set(resume_skills)
    )

    if len(job_skills) > 0:

        match_score = round(
            (
                len(matched_skills)
                /
                len(job_skills)
            ) * 100,
            2
        )

    else:
        match_score = 0

    suggestions = (
        "Excellent Match!"
        if match_score >= 80
        else
        "Add missing skills to improve matching."
    )

    return render_template(
        "result.html",
        ats_score=match_score,
        resume_score=match_score,
        ai_score=match_score,
        role="Job Match Analysis",
        level=(
            "🔥 Excellent"
            if match_score >= 80
            else "👍 Good"
        ),
        matched=matched_skills,
        missing=missing_skills,
        missing_skills=missing_skills,
        match_score=match_score,
        suggestions=suggestions,
        feedback=[
            f"Matched {len(matched_skills)} skills",
            f"Missing {len(missing_skills)} skills",
            f"Job Match Score: {match_score}%"
        ]
    )

# ---------------- REPORT ----------------

@app.route("/report")
def report():

    report_path = os.path.join(
        REPORT_FOLDER,
        "report.txt"
    )

    if not os.path.exists(
        report_path
    ):

        with open(
            report_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "ATS Resume Analyzer Report"
            )

    return send_file(
        report_path,
        as_attachment=True
    )

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(
        debug=True
    )