# server.py
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

# Flask app configuration
app = Flask(__name__, template_folder="../templates", static_folder="../static")
CORS(app, resources={r"/*": {"origins": "*"}})

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("❌ MONGO_URI not set in .env file")
    exit(1)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print("✅ MongoDB Connected")
except Exception as e:
    print(f"❌ MongoDB Connection Failed: {e}")
    exit(1)

db = client["SoulixDB"]

# SMTP Settings
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

# OTP Generation
def gen_otp(n=6):
    return "".join(str(random.randint(0, 9)) for _ in range(n))

# Email OTP
def send_email_otp(to_email, otp):
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS]):
        print(f"❌ SMTP credentials missing")
        return False
    try:
        msg = MIMEText(f"Your OTP is: {otp} (expires in 5 mins)")
        msg["Subject"] = "Serenity Space OTP"
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        return False

# Routes
@app.route('/')
def home():
    return render_template('register.html')

@app.route('/signup-request', methods=['POST'])
def signup_request():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data received"}), 400
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        if not all([name, email, password]):
            return jsonify({"message": "Missing fields"}), 400
        if db.users_signup.find_one({"email": email.lower()}):
            return jsonify({"message": "User exists"}), 400
        otp = gen_otp()
        temp_doc = {
            "name": name,
            "email": email.lower(),
            "password_hash": generate_password_hash(password),
            "otp_hash": generate_password_hash(otp),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
        }
        db.temp_users.replace_one({"email": email.lower()}, temp_doc, upsert=True)
        if send_email_otp(email, otp):
            return jsonify({"message": "OTP sent to your email"}), 200
        else:
            return jsonify({"message": "Failed to send OTP, try again"}), 500
    except Exception as e:
        print(f"Error in signup_request: {e}")
        return jsonify({"message": "Server error"}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        if not email or not otp:
            return jsonify({"message": "Missing email or OTP"}), 400
        temp = db.temp_users.find_one({"email": email.lower()})
        if not temp:
            return jsonify({"message": "No pending signup found"}), 401
        if datetime.now(timezone.utc) > temp["expires_at"]:
            return jsonify({"message": "OTP expired"}), 401
        if not check_password_hash(temp["otp_hash"], otp):
            return jsonify({"message": "Invalid OTP"}), 401
        db.users_signup.insert_one({
            "name": temp["name"],
            "email": email.lower(),
            "password_hash": temp["password_hash"],
            "created_at": datetime.now(timezone.utc)
        })
        db.temp_users.delete_one({"email": email.lower()})
        return jsonify({"message": "Signup complete!"}), 201
    except Exception as e:
        print(f"Error in verify_otp: {e}")
        return jsonify({"message": "Server error"}), 500

@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        if not email:
            return jsonify({"message": "Missing email"}), 400
        temp = db.temp_users.find_one({"email": email.lower()})
        if not temp:
            return jsonify({"message": "No pending signup found"}), 400
        otp = gen_otp()
        temp_doc = {
            "name": temp["name"],
            "email": email.lower(),
            "password_hash": temp["password_hash"],
            "otp_hash": generate_password_hash(otp),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
        }
        db.temp_users.replace_one({"email": email.lower()}, temp_doc, upsert=True)
        if send_email_otp(email, otp):
            return jsonify({"message": "OTP resent to your email"}), 200
        else:
            return jsonify({"message": "Failed to resend OTP, try again"}), 500
    except Exception as e:
        print(f"Error in resend_otp: {e}")
        return jsonify({"message": "Server error"}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            return jsonify({"message": "Missing email or password"}), 400
        user = db.users_signup.find_one({"email": email.lower()})
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"message": "Invalid email or password"}), 401
        return jsonify({"message": "Login successful!"}), 200
    except Exception as e:
        print(f"Error in login: {e}")
        return jsonify({"message": "Server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
