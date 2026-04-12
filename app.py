import sqlite3
from flask import Flask, render_template, request, redirect, session, flash, Response, jsonify
import os
import random
import uuid
import base64
from datetime import datetime

app = Flask(__name__)
app.secret_key = "voting_secret_platinum"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")
os.makedirs(os.path.join(app.root_path, "static", "uploads"), exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        firstname TEXT NOT NULL,
        lastname TEXT NOT NULL,
        age INTEGER,
        email TEXT,
        gender TEXT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone_number TEXT UNIQUE,
        otp_code TEXT,
        is_verified INTEGER DEFAULT 0,
        voted INTEGER DEFAULT 0
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        avatar_file TEXT DEFAULT 'default.png',
        votes INTEGER DEFAULT 0
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vote_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id TEXT UNIQUE NOT NULL,
        username TEXT NOT NULL,
        candidate_id INTEGER NOT NULL,
        ip_address TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    try:
        cursor.execute("ALTER TABLE vote_logs ADD COLUMN photo_filename TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO settings (key, value) VALUES ('election_deadline', '2030-12-31T23:59:00')")

    cursor.execute("SELECT COUNT(*) FROM candidates")
    if cursor.fetchone()[0] == 0:
        default_candidates = [
            ("🦁 Saketh", "saketh.png"), 
            ("🚀 Karthikeya", "karthikeya.png"), 
            ("💎 Bhargav", "bhargav.png")
        ]
        cursor.executemany("INSERT INTO candidates (name, avatar_file) VALUES (?, ?)", default_candidates)
        
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_users = [
            ("Admin", "System", 30, "admin@example.com", "Other", "admin", "admin123", "0000000000", "000000", 1),
            ("Harshith", "User", 20, "harshith@example.com", "Male", "harshith", "password123", "1111111111", "000000", 1),
            ("Pragnay", "User", 20, "pragnay@example.com", "Male", "pragnay", "password123", "2222222222", "000000", 1),
            ("Yashwnath", "User", 20, "yashwnath@example.com", "Male", "yashwnath", "password123", "3333333333", "000000", 1),
            ("Chandra", "User", 20, "chandra@example.com", "Male", "chandra", "password123", "4444444444", "000000", 1)
        ]
        cursor.executemany('''
        INSERT INTO users (firstname, lastname, age, email, gender, username, password, phone_number, otp_code, is_verified)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', default_users)
        
    conn.commit()
    conn.close()

with app.app_context():
    init_db()

@app.route("/")
def home():
    if "user" in session:
        return redirect("/vote")
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        age = request.form["age"]
        email = request.form["email"]
        gender = request.form["gender"]
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO users (firstname, lastname, age, email, gender, username, password, phone_number, otp_code, is_verified)
            VALUES (?,?,?,?,?,?,?,NULL,NULL,1)
            ''', (firstname, lastname, age, email, gender, username, password))
            conn.commit()
            
            flash("Account successfully created! You may now log in.", "success")
            return redirect("/")
            
        except sqlite3.IntegrityError as e:
            if "username" in str(e).lower():
                flash("Username already exists!", "error")
            else:
                flash("Phone number or email already in use!", "error")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if "verify_username" not in session:
        return redirect("/")
    username = session["verify_username"]
    
    if request.method == "POST":
        entered_otp = request.form["otp"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT otp_code FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        
        if user and user["otp_code"] == entered_otp:
            cursor.execute("UPDATE users SET is_verified = 1, otp_code = NULL WHERE username=?", (username,))
            conn.commit()
            conn.close()
            session.pop("verify_username", None)
            flash("Phone number verified successfully! You may now log in.", "success")
            return redirect("/")
        else:
            conn.close()
            flash("Invalid OTP code. Please try again.", "error")
            
    return render_template("verify_otp.html", username=username)

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session["user"] = username
        return redirect("/vote")
    else:
        flash("Invalid Username or Password", "error")
        return redirect("/")

def is_voting_open():
    conn = get_db_connection()
    deadline_row = conn.execute("SELECT value FROM settings WHERE key='election_deadline'").fetchone()
    conn.close()
    if not deadline_row: return True
    deadline = datetime.fromisoformat(deadline_row["value"])
    return datetime.now() < deadline

@app.route("/api/deadline")
def api_deadline():
    conn = get_db_connection()
    deadline_row = conn.execute("SELECT value FROM settings WHERE key='election_deadline'").fetchone()
    conn.close()
    if not deadline_row: return jsonify({"deadline": None, "isOpen": True})
    deadline = datetime.fromisoformat(deadline_row["value"])
    return jsonify({"deadline": deadline_row["value"], "isOpen": datetime.now() < deadline})

@app.route("/vote")
def vote():
    if "user" not in session: return redirect("/")
    conn = get_db_connection()
    cursor = conn.cursor()
    candidates = cursor.execute("SELECT * FROM candidates").fetchall()
    user_info = cursor.execute("SELECT voted FROM users WHERE username=?", (session["user"],)).fetchone()
    conn.close()
    
    has_voted = user_info["voted"] == 1 if user_info else False
    is_open = is_voting_open()
    return render_template("vote.html", candidates=candidates, has_voted=has_voted, is_open=is_open)

@app.route("/cast_vote", methods=["POST"])
def cast_vote():
    if "user" not in session: return redirect("/")
    
    if not is_voting_open():
        flash("The election deadline has passed! Voting is locked.", "error")
        return redirect("/results")

    candidate_id = request.form.get("candidate")
    if not candidate_id:
        flash("Please select a candidate!", "error")
        return redirect("/vote")

    username = session["user"]
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_data = cursor.execute("SELECT voted FROM users WHERE username=?", (username,)).fetchone()
    if user_data and user_data["voted"] == 1:
        flash("You already voted! You cannot vote again.", "error")
        conn.close()
        return redirect("/results")

    receipt_id = "VOTE-" + uuid.uuid4().hex[:10].upper()
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

    photo_data = request.form.get("voter_photo")
    photo_filename = None
    if photo_data and ',' in photo_data:
        try:
            head, base64_data = photo_data.split(',', 1)
            image_data = base64.b64decode(base64_data)
            photo_filename = f"{receipt_id}.jpg"
            photo_path = os.path.join(app.root_path, "static", "uploads", photo_filename)
            with open(photo_path, "wb") as f:
                f.write(image_data)
        except Exception as e:
            print(f"Error saving photo: {e}")

    cursor.execute("UPDATE candidates SET votes = votes + 1 WHERE id=?", (candidate_id,))
    cursor.execute("UPDATE users SET voted=1 WHERE username=?", (username,))
    cursor.execute(
        "INSERT INTO vote_logs (receipt_id, username, candidate_id, ip_address, photo_filename) VALUES (?,?,?,?,?)",
        (receipt_id, username, candidate_id, ip_address, photo_filename)
    )

    conn.commit()
    conn.close()
    
    session["receipt_id"] = receipt_id
    flash("Vote cast successfully!", "success")
    return redirect("/receipt")

@app.route("/receipt")
def receipt():
    if "user" not in session or "receipt_id" not in session:
        return redirect("/results")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    log = cursor.execute('''
        SELECT v.receipt_id, v.timestamp, c.name as candidate_name 
        FROM vote_logs v JOIN candidates c ON v.candidate_id = c.id
        WHERE v.receipt_id = ?
    ''', (session["receipt_id"],)).fetchone()
    conn.close()
    
    if not log: return redirect("/results")
    return render_template("receipt.html", log=log, username=session["user"])

@app.route("/api/results")
def api_results():
    conn = get_db_connection()
    results = conn.execute("SELECT name, votes FROM candidates ORDER BY votes DESC").fetchall()
    conn.close()
    return jsonify([{"name": r["name"], "votes": r["votes"]} for r in results])

@app.route("/results")
def result():
    conn = get_db_connection()
    results = conn.execute("SELECT * FROM candidates ORDER BY votes DESC").fetchall()
    conn.close()
    return render_template("results.html", results=results)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect("/")

@app.route("/admin")
def admin():
    if session.get("user") != "admin": return redirect("/")
    
    conn = get_db_connection()
    logs = conn.execute('''
        SELECT v.id, v.receipt_id, v.username, v.ip_address, v.timestamp, v.photo_filename, c.name as candidate_name 
        FROM vote_logs v JOIN candidates c ON v.candidate_id = c.id ORDER BY v.timestamp DESC
    ''').fetchall()
    
    suspicious_ips = [row["ip_address"] for row in conn.execute('''
        SELECT ip_address, COUNT(*) as count FROM vote_logs GROUP BY ip_address HAVING count > 1
    ''').fetchall()]
    
    candidates = conn.execute("SELECT * FROM candidates").fetchall()
    deadline = conn.execute("SELECT value FROM settings WHERE key='election_deadline'").fetchone()["value"]
    
    conn.close()
    return render_template("admin.html", logs=logs, suspicious_ips=suspicious_ips, candidates=candidates, deadline=deadline)

@app.route("/admin/export")
def export_csv():
    if session.get("user") != "admin": return redirect("/")
    conn = get_db_connection()
    logs = conn.execute('''
        SELECT v.receipt_id, v.timestamp, v.username, c.name, v.ip_address
        FROM vote_logs v JOIN candidates c ON v.candidate_id = c.id ORDER BY v.timestamp DESC
    ''').fetchall()
    conn.close()

    def generate():
        data = ["Receipt ID,Timestamp,Username,Candidate Picked,IP Address\n"]
        for log in logs:
            data.append(f"{log['receipt_id']},{log['timestamp']},{log['username']},{log['name']},{log['ip_address']}\n")
        return "".join(data)

    return Response(generate(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=vote_logs.csv"})

@app.route("/admin/settings/deadline", methods=["POST"])
def update_deadline():
    if session.get("user") != "admin": return redirect("/")
    new_dl = request.form.get("deadline")
    conn = get_db_connection()
    conn.execute("UPDATE settings SET value=? WHERE key='election_deadline'", (new_dl,))
    conn.commit()
    conn.close()
    flash("Election deadline updated!", "success")
    return redirect("/admin")

@app.route("/admin/candidate/add", methods=["POST"])
def add_candidate():
    if session.get("user") != "admin": return redirect("/")
    new_name = request.form.get("name")
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO candidates (name) VALUES (?)", (new_name,))
        conn.commit()
        flash(f"Candidate {new_name} added successfully!", "success")
    except:
        flash("Error adding candidate (must be unique).", "error")
    conn.close()
    return redirect("/admin")

@app.route("/admin/candidate/delete/<int:cid>", methods=["POST"])
def delete_candidate(cid):
    if session.get("user") != "admin": return redirect("/")
    conn = get_db_connection()
    conn.execute("DELETE FROM candidates WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    flash("Candidate removed from ballot.", "success")
    return redirect("/admin")

@app.route("/revoke_vote/<int:log_id>", methods=["POST"])
def revoke_vote(log_id):
    if session.get("user") != "admin": return redirect("/")
    conn = get_db_connection()
    log = conn.execute("SELECT username, candidate_id FROM vote_logs WHERE id = ?", (log_id,)).fetchone()
    if log:
        conn.execute("UPDATE candidates SET votes = votes - 1 WHERE id = ?", (log["candidate_id"],))
        conn.execute("UPDATE users SET voted = 0 WHERE username = ?", (log["username"],))
        conn.execute("DELETE FROM vote_logs WHERE id = ?", (log_id,))
        conn.commit()
        flash(f"Vote from '{log['username']}' completely revoked.", "success")
    conn.close()
    return redirect("/admin")

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)