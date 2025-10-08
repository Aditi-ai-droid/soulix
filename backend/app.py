import os
import random
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder="templates")
CORS(app, resources={r"/*": {"origins": ["http://localhost:5000", "http://localhost:3000"]}})  # Allow frontend origins

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("❌ MONGO_URI not set in .env file")
    exit(1)

try:
    client = MongoClient(MONGO_URI, tls=True, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print("✅ MongoDB Connected")
except Exception as e:
    print(f"❌ MongoDB Connection Failed: {e}")
    exit(1)

db = client["SoulixDB"]

# OTP Settings
OTP_LENGTH = 6
OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_LIMIT = 3
OTP_RESEND_COOLDOWN = 30

# SMTP Settings
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

if not all([SMTP_HOST, SMTP_USER, SMTP_PASS]):
    print("⚠️ SMTP settings incomplete. OTP emails will not be sent.")

# Helper Functions
def gen_otp(n=OTP_LENGTH):
    return "".join(str(random.randint(0, 9)) for _ in range(n))

def send_email_otp(to_email, otp):
    subject = "Your Serenity Space OTP"
    body = f"Your OTP is: {otp} (expires in {OTP_TTL_SECONDS//60} mins)"
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = to_email

            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())
            server.quit()
            print(f"✅ OTP sent to {to_email}")
            return True
        except Exception as e:
            print(f"SMTP error: {e}")
            print(f"[DEV OTP] {to_email}: {otp}")
            return False
    else:
        print(f"[DEV OTP] {to_email}: {otp}")
        return False

def serialize_user(user):
    return {
        "_id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "avatar": user.get("avatar", ""),
        "created_at": user["created_at"].isoformat() if "created_at" in user else ""
    }

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/test")
def test():
    return jsonify({"message": "Server running"})

@app.route("/signup-request", methods=["POST"])
def signup_request():
    try:
        data = request.get_json() or {}
        name, email, password = data.get("name"), data.get("email"), data.get("password")
        if not name or not email or not password:
            return jsonify({"message": "Name, email, password required"}), 400

        print(f"Checking if user exists: {email}")
        if db.users.find_one({"email": email}):
            return jsonify({"message": "User exists"}), 400

        existing = db.temp_users.find_one({"email": email})
        now = datetime.now(timezone.utc)
        if existing:
            last_sent = existing.get("last_sent_at", now - timedelta(seconds=9999))
            if (now - last_sent).total_seconds() < OTP_RESEND_COOLDOWN:
                wait = OTP_RESEND_COOLDOWN - int((now - last_sent).total_seconds())
                return jsonify({"message": f"Try again after {wait}s"}), 429

        otp = gen_otp()
        otp_hash = generate_password_hash(otp)
        expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)

        temp_doc = {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "otp_hash": otp_hash,
            "expires_at": expires_at,
            "attempts": 0,
            "resend_count": (existing.get("resend_count", 0) + 1) if existing else 1,
            "last_sent_at": now
        }

        print(f"Inserting temp user: {temp_doc}")
        db.temp_users.replace_one({"email": email}, temp_doc, upsert=True)
        if send_email_otp(email, otp):
            return jsonify({"message": "OTP sent", "email": email, "otp_debug": otp}), 200
        else:
            return jsonify({"message": "Failed to send OTP"}), 500
    except Exception as e:
        print(f"signup-request error: {e}")
        return jsonify({"message": "Server error", "error": str(e)}), 500

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json() or {}
        email, otp = data.get("email"), data.get("otp")
        if not email or not otp:
            return jsonify({"message": "Email and OTP required"}), 400

        temp = db.temp_users.find_one({"email": email})
        print(f"Temp user found: {temp}")
        if not temp:
            return jsonify({"message": "No OTP requested"}), 400

        now = datetime.now(timezone.utc)
        if now > temp["expires_at"]:
            db.temp_users.delete_one({"email": email})
            return jsonify({"message": "OTP expired"}), 400

        if temp["attempts"] >= OTP_MAX_ATTEMPTS:
            db.temp_users.delete_one({"email": email})
            return jsonify({"message": "Max attempts exceeded"}), 403

        if not check_password_hash(temp["otp_hash"], otp):
            db.temp_users.update_one({"email": email}, {"$inc": {"attempts": 1}})
            return jsonify({"message": "Invalid OTP"}), 401

        user_id = db.users.insert_one({
            "name": temp["name"],
            "email": email,
            "password": temp["password_hash"],
            "created_at": now,
            "avatar": ""
        }).inserted_id

        print(f"User created: {user_id}")
        db.temp_users.delete_one({"email": email})
        user = db.users.find_one({"_id": user_id})
        return jsonify({"message": "User created", "user": serialize_user(user)}), 201
    except Exception as e:
        print(f"verify-otp error: {e}")
        return jsonify({"message": "Server error", "error": str(e)}), 500

@app.route("/resend-otp", methods=["POST"])
def resend_otp():
    try:
        data = request.get_json() or {}
        email = data.get("email")
        if not email:
            return jsonify({"message": "Email required"}), 400

        temp = db.temp_users.find_one({"email": email})
        if not temp:
            return jsonify({"message": "No pending OTP"}), 400

        now = datetime.now(timezone.utc)
        last_sent = temp.get("last_sent_at", now - timedelta(seconds=9999))
        if (now - last_sent).total_seconds() < OTP_RESEND_COOLDOWN:
            return jsonify({"message": "Wait before resending"}), 429

        if temp.get("resend_count", 0) >= OTP_RESEND_LIMIT:
            return jsonify({"message": "Resend limit reached"}), 429

        otp = gen_otp()
        otp_hash = generate_password_hash(otp)
        expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)

        db.temp_users.update_one({"email": email}, {"$set": {
            "otp_hash": otp_hash,
            "expires_at": expires_at,
            "last_sent_at": now,
            "attempts": 0,
            "resend_count": temp.get("resend_count", 0) + 1
        }})

        if send_email_otp(email, otp):
            return jsonify({"message": "OTP resent", "otp_debug": otp}), 200
        else:
            return jsonify({"message": "Failed to resend OTP"}), 500
    except Exception as e:
        print(f"resend-otp error: {e}")
        return jsonify({"message": "Server error", "error": str(e)}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json() or {}
        email, password = data.get("email"), data.get("password")
        if not email or not password:
            return jsonify({"message": "Email and password required"}), 400

        user = db.users.find_one({"email": email})
        if not user:
            return jsonify({"message": "User not found"}), 404

        if not check_password_hash(user["password"], password):
            return jsonify({"message": "Invalid password"}), 401

        return jsonify({"message": "Login successful", "user": serialize_user(user)}), 200
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({"message": "Server error", "error": str(e)}), 500

# Run the app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)