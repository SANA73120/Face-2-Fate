from flask import Flask, request, redirect, session, flash, render_template, jsonify
import os
import json
import threading
from werkzeug.utils import secure_filename
import mysql.connector
from flask import send_from_directory
from dotenv import load_dotenv

from pipeline import process_video_pipeline
from utils import UPLOAD_FOLDER

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-insecure-key")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    db = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "emotion_aware"),
        port=int(os.getenv("DB_PORT", 3306))
    )
    db.ping(reconnect=True)
    return db


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():
    return render_template("index.html", logged_in="user_id" in session)

@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect("/questions")  # already logged in
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    if "user_id" in session:
        return redirect("/questions")
    return render_template("signup.html", logged_in=False)

@app.route("/questions")
def questions_page():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("questions.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/terms")
def terms_page():
    return render_template("terms.html", logged_in="user_id" in session)

@app.route("/privacy")
def privacy_page():
    return render_template("privacy.html", logged_in="user_id" in session)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ============================================================
# SIGNUP
# ============================================================

@app.route("/register-user", methods=["POST"])
def register_user():

    username = request.form.get("username")
    email = request.form.get("email").strip().lower()
    password = request.form.get("password").strip()

    if not username or not email or not password:
        flash("All fields are required.")
        return redirect("/signup")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Check if email is already registered
    cursor.execute("SELECT u_id FROM users WHERE email=%s", (email,))
    existing = cursor.fetchone()

    if existing:
        cursor.close()
        db.close()
        flash("An account with that email already exists. Please log in.")
        return redirect("/signup")

    cursor.execute(
        "INSERT INTO users (username,email,password) VALUES (%s,%s,%s)",
        (username, email, password)
    )

    db.commit()
    cursor.close()
    db.close()

    return redirect("/login")


# ============================================================
# LOGIN
# ============================================================

@app.route("/login-user", methods=["POST"])
def login_user():

    email = request.form.get("email").strip().lower()
    password = request.form.get("password").strip()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    cursor.close()
    db.close()

    if not user:
        flash("Account does not exist")
        return redirect("/login")

    if user["password"] != password:
        flash("Incorrect password")
        return redirect("/login")

    session["user_id"] = user["u_id"]

    return redirect("/questions")


# ============================================================
# RESET-PASSWORD
# ============================================================

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password_page():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip().lower()
        new_password = request.form.get("new_password").strip()

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND email=%s",
            (username, email)
        )
        user = cursor.fetchone()

        if not user:
            flash("No account found with that username and email")
            cursor.close()
            db.close()
            return redirect("/reset-password")

        cursor.execute(
            "UPDATE users SET password=%s WHERE u_id=%s",
            (new_password, user["u_id"])
        )
        db.commit()
        cursor.close()
        db.close()

        flash("Password updated successfully!")
        return redirect("/login")

    return render_template("reset_password.html", logged_in=False)


# ============================================================
# FORGOT USERNAME
# ============================================================

@app.route("/forgot-username", methods=["GET", "POST"])
def forgot_username_page():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        password = request.form.get("password").strip()

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )
        user = cursor.fetchone()

        cursor.close()
        db.close()

        if not user:
            flash("No account found with that email")
            return redirect("/forgot-username")

        if user["password"] != password:
            flash("Incorrect password")
            return redirect("/forgot-username")

        flash(f"Your username is: {user['username']}")
        return redirect("/forgot-username")

    return render_template("forgot_username.html", logged_in=False)


# ============================================================
# UPLOAD PAGE
# ============================================================

@app.route("/upload-page")
def upload_page():

    if "user_id" not in session:
        return redirect("/login")

    q_id = request.args.get("q_id")
    u_id = session.get("user_id")

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT v_id, vid_path, status FROM video WHERE q_id=%s AND u_id=%s ORDER BY v_id DESC",
        (q_id, u_id)
    )

    history = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("upload.html", q_id=q_id, history=history)


# ============================================================
# UPLOAD VIDEO
# ============================================================

@app.route("/upload", methods=["POST"])
def upload_video():

    if "user_id" not in session:
        return redirect("/login")

    video_file = request.files["video"]
    original_filename = secure_filename(video_file.filename)

    q_id = request.form.get("q_id")
    u_id = session.get("user_id")

    # INSERT ROW FIRST (with empty placeholder) TO GET v_id
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO video (u_id, q_id, vid_path, status) VALUES (%s,%s,%s,%s)",
        (u_id, q_id, "", "processing")
    )

    db.commit()
    v_id = cursor.lastrowid

    # BUILD UNIQUE FILENAME USING v_id — prevents any collision
    unique_filename = f"{v_id}_{original_filename}"
    video_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    video_file.save(video_path)

    # UPDATE ROW WITH ACTUAL PATH
    cursor.execute("UPDATE video SET vid_path=%s WHERE v_id=%s", (video_path, v_id))
    db.commit()

    cursor.close()
    db.close()

    # START BACKGROUND PIPELINE
    thread = threading.Thread(
        target=process_video_pipeline,
        args=(video_path, u_id, q_id, v_id)
    )

    thread.start()

    return jsonify({"status": "processing", "v_id": v_id})


# ============================================================
# STATUS CHECK
# ============================================================

@app.route("/status/<int:v_id>")
def check_status(v_id):

    if "user_id" not in session:
        return jsonify({"status": "error"})

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT status FROM video WHERE v_id=%s",
        (v_id,)
    )

    row = cursor.fetchone()

    cursor.close()
    db.close()

    if not row:
        return jsonify({"status": "error"})

    return jsonify({"status": row["status"], "v_id": v_id})


# ============================================================
# DELETE VIDEO
# ============================================================

@app.route("/delete/<int:v_id>")
def delete_video(v_id):

    if "user_id" not in session:
        return redirect("/login")

    u_id = session.get("user_id")

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT q_id FROM video WHERE v_id=%s AND u_id=%s",
        (v_id, u_id)
    )

    row = cursor.fetchone()

    if not row:
        return "Video not found"

    q_id = row[0]

    cursor.execute("DELETE FROM video_analysis WHERE v_id=%s", (v_id,))
    cursor.execute("DELETE FROM audio_analysis WHERE v_id=%s", (v_id,))
    cursor.execute("DELETE FROM text_analysis WHERE v_id=%s", (v_id,))
    cursor.execute("DELETE FROM report WHERE v_id=%s", (v_id,))
    cursor.execute("DELETE FROM video WHERE v_id=%s", (v_id,))

    db.commit()
    cursor.close()
    db.close()

    return redirect(f"/upload-page?q_id={q_id}")


# ============================================================
# REPORT PAGE
# ============================================================

@app.route("/report/<int:v_id>")
def report_page(v_id):

    if "user_id" not in session:
        return redirect("/login")

    u_id = session.get("user_id")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            v.vid_path,
            va.eye_contact_percent,
            va.blink_rate,
            va.hand_movement,
            va.emotion_distribution,
            aa.duration,
            aa.energy_var,
            aa.pitch_var,
            ta.transcript,
            ta.filler_count,
            r.score,
            r.breakdown,
            r.main_feedback
        FROM video v
        LEFT JOIN video_analysis va ON v.v_id = va.v_id
        LEFT JOIN audio_analysis aa ON v.v_id = aa.v_id
        LEFT JOIN text_analysis ta ON v.v_id = ta.v_id
        LEFT JOIN report r ON v.v_id = r.v_id
        WHERE v.v_id=%s AND v.u_id=%s
        """,
        (v_id, u_id)
    )

    data = cursor.fetchone()

    cursor.close()
    db.close()

    emotion_distribution = (
        json.loads(data["emotion_distribution"])
        if isinstance(data["emotion_distribution"], str)
        else data["emotion_distribution"] or {}
    )

    breakdown = (
        json.loads(data["breakdown"])
        if isinstance(data["breakdown"], str)
        else data["breakdown"] or {}
    )

    return render_template(
        "report.html",

        video_path=data["vid_path"],
        score=data["score"],
        breakdown=breakdown,
        main_feedback=data["main_feedback"],

        eye_contact=data["eye_contact_percent"],
        blink_rate=data["blink_rate"],
        hand_movement=data["hand_movement"],
        pitch_var=data["pitch_var"],
        energy_var=data["energy_var"],
        emotion_distribution=emotion_distribution,

        duration=data["duration"],
        avg_pitch=data["pitch_var"],
        filler_count=data["filler_count"],
        transcript=data["transcript"],
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)