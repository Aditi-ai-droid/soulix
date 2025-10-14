import os
import random
import re
import json
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from bson import ObjectId
from google.genai import Client  # ✅ Gemini client

# ---------- Load Environment Variables ----------
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# ---------- MongoDB ----------
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["SoulixDB"]
print("✅ MongoDB Connected")

# ---------- SMTP ----------
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

# ---------- OTP Settings ----------
OTP_LENGTH = 6
OTP_TTL_SECONDS = 300  # 5 minutes


# ---------- Helper Functions ----------
def gen_otp(n=OTP_LENGTH):
    return "".join(str(random.randint(0, 9)) for _ in range(n))


def send_email_otp(to_email, otp):
    """Send OTP email"""
    try:
        msg = MIMEText(f"""
        💙 Hello from Soulix,

        Your One-Time Password (OTP) is: {otp}
        It will expire in 5 minutes.

        Stay calm, stay connected 🌿
        — Team Soulix
        """)
        msg["Subject"] = "Your Soulix Verification Code 💙"
        msg["From"] = f"Soulix 💙 <{SMTP_USER}>"
        msg["To"] = to_email

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())
        server.quit()
        print(f"✅ OTP sent successfully to {to_email}")
        return True

    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False


# ---------- AUTH ROUTES ----------
@app.route("/signup-request", methods=["POST"])
def signup_request():
    try:
        data = request.get_json()
        name, email, password = data.get("name"), data.get("email"), data.get("password")

        if not all([name, email, password]):
            return jsonify({"message": "Name, email, and password required"}), 400

        strong_password = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^A-Za-z0-9]).{8,}$')
        if not strong_password.match(password):
            return jsonify({"message": "Weak password"}), 400

        email = email.lower()
        if db.users_signup.find_one({"email": email}):
            return jsonify({"message": "User already exists"}), 400

        otp = gen_otp()
        otp_hash = generate_password_hash(otp)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=OTP_TTL_SECONDS)

        db.temp_users.replace_one({"email": email}, {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "otp_hash": otp_hash,
            "expires_at": expires_at
        }, upsert=True)

        if send_email_otp(email, otp):
            return jsonify({"message": "OTP sent to email"}), 200
        else:
            return jsonify({"message": "Failed to send OTP"}), 500

    except Exception as e:
        print("signup-request error:", e)
        return jsonify({"message": "Server error"}), 500


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json()
        email, otp = data.get("email"), data.get("otp")

        temp = db.temp_users.find_one({"email": email})
        if not temp:
            return jsonify({"message": "No pending signup"}), 401

        expires_at = temp["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if datetime.now(timezone.utc) > expires_at:
            db.temp_users.delete_one({"email": email})
            return jsonify({"message": "OTP expired"}), 401

        if not check_password_hash(temp["otp_hash"], str(otp).strip()):
            return jsonify({"message": "Invalid OTP"}), 401

        db.users_signup.insert_one({
            "name": temp["name"],
            "email": email,
            "password_hash": temp["password_hash"],
            "created_at": datetime.now(timezone.utc)
        })
        db.temp_users.delete_one({"email": email})

        session["logged_in"] = True
        session["user_email"] = email
        session["user_name"] = temp["name"]

        return jsonify({"message": "Signup complete"}), 201

    except Exception as e:
        print("verify-otp error:", e)
        return jsonify({"message": "Server error"}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email, password = data.get("email"), data.get("password")
        email = email.lower()
        user = db.users_signup.find_one({"email": email})

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"message": "Invalid credentials"}), 401

        session["logged_in"] = True
        session["user_email"] = email
        session["user_name"] = user.get("name", email.split("@")[0])
        return jsonify({"message": "Login successful"}), 200

    except Exception as e:
        return jsonify({"message": "Server error"}), 500


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


# ---------- CHATBOT ----------
gemini_client = Client(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAo9TU-kdRmbzl_RzwowSflywgHuiWtH7I"))

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        message = data.get("message", "")
        if not message:
            return jsonify({"reply": "Type something 💬"}), 400

        try:
            gemini_response = gemini_client.models.generate_content(
                model="models/gemini-2.5-pro",
                contents=[{"role": "user", "parts": [{"text": message}]}]
            )
            reply = gemini_response.text.strip()
        except Exception:
            reply = "I'm here for you 💙"

        db.chat_logs.insert_one({
            "email": session.get("user_email", "guest"),
            "user_message": message,
            "bot_reply": reply,
            "timestamp": datetime.now(timezone.utc)
        })
        return jsonify({"reply": reply}), 200
    except Exception as e:
        print("Chat error:", e)
        return jsonify({"reply": "Server error"}), 500


# ---------- BOOK SYSTEM (Soulix Library) ----------

@app.route("/books", methods=["GET"])
def get_books():
    books = list(db.books.find({}, {"title": 1, "author": 1, "cover_url": 1, "total_pages": 1}))
    for b in books:
        b["_id"] = str(b["_id"])
    return jsonify({"books": books}), 200


@app.route("/books/<book_id>/pages", methods=["GET"])
def get_pages(book_id):
    try:
        start = int(request.args.get("start", 0))
        limit = int(request.args.get("limit", 1))
        pages = list(
            db.book_pages.find(
                {"book_id": ObjectId(book_id), "page_index": {"$gte": start, "$lt": start + limit}}
            ).sort("page_index", 1)
        )
        total = db.books.find_one({"_id": ObjectId(book_id)}, {"total_pages": 1})
        for p in pages:
            p["_id"] = str(p["_id"])
        return jsonify({"pages": pages, "total_pages": total.get("total_pages", 0)}), 200
    except Exception as e:
        print("❌ Page fetch error:", e)
        return jsonify({"message": "Error loading pages"}), 500


@app.route("/progress", methods=["POST"])
def save_progress():
    data = request.get_json()
    email = session.get("user_email")
    book_id = data.get("book_id")
    page_index = data.get("page_index")
    if not email:
        return jsonify({"message": "Login required"}), 401
    db.progress.update_one(
        {"email": email, "book_id": ObjectId(book_id)},
        {"$set": {"page_index": page_index, "updated_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    return jsonify({"message": "Progress saved"}), 200


@app.route("/progress/<book_id>", methods=["GET"])
def get_progress(book_id):
    email = session.get("user_email")
    if not email:
        return jsonify({"message": "Login required"}), 401
    progress = db.progress.find_one({"email": email, "book_id": ObjectId(book_id)}, {"_id": 0})
    return jsonify({"progress": progress or {}}), 200


# ---------- TEST ----------
@app.route("/test")
def test():
    return jsonify({"message": "Soulix backend active ✅"})


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
