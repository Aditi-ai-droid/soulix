import os, random
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=5000)
db = client["SoulixDB"]
print("✅ MongoDB Connected")

# SMTP setup
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

# Helper functions
def gen_otp(n=6):
    return "".join(str(random.randint(0,9)) for _ in range(n))

def send_email_otp(to_email, otp):
    try:
        msg = MIMEText(f"Your OTP is: {otp} (valid for 5 mins)")
        msg["Subject"]="Serenity Space OTP"
        msg["From"]=SMTP_USER
        msg["To"]=to_email
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())
        server.quit()
        print(f"✅ OTP sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send OTP: {e}")
        return False

# Signup request
@app.route('/signup-request', methods=['POST'])
def signup_request():
    data = request.get_json()
    name,email,password=data.get('name'),data.get('email'),data.get('password')
    if not all([name,email,password]): 
        return jsonify({"message":"Missing fields"}),400

    email=email.lower()
    if db.users_signup.find_one({"email":email}):
        return jsonify({"message":"User already exists"}),400

    otp=gen_otp()
    temp_doc={
        "name":name,
        "email":email,
        "password_hash":generate_password_hash(password),
        "otp_hash":generate_password_hash(otp),
        "expires_at": datetime.now(timezone.utc)+timedelta(minutes=5)
    }
    db.temp_users.replace_one({"email":email}, temp_doc, upsert=True)
    if send_email_otp(email, otp):
        return jsonify({"message":"OTP sent to your email"}),200
    else:
        return jsonify({"message":"Failed to send OTP"}),500

# OTP verification
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email,otp=data.get('email'),data.get('otp')
    if not all([email,otp]): return jsonify({"message":"Missing fields"}),400

    email=email.lower()
    temp=db.temp_users.find_one({"email":email})
    if not temp: return jsonify({"message":"No pending signup"}),401

    expires_at=temp["expires_at"]
    if isinstance(expires_at,str):
        expires_at=datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc)>expires_at:
        db.temp_users.delete_one({"email":email})
        return jsonify({"message":"OTP expired"}),401

    if not check_password_hash(temp["otp_hash"], str(otp).strip()):
        return jsonify({"message":"Invalid OTP"}),401

    db.users_signup.insert_one({
        "name":temp["name"],
        "email":email,
        "password_hash":temp["password_hash"],
        "created_at":datetime.now(timezone.utc)
    })
    db.temp_users.delete_one({"email":email})

    # Automatically login after signup
    session['user_email'] = email
    print(f"✅ Signup complete for {email}")
    return jsonify({"message":"Signup complete! Redirect to avatar"}),201

# Login route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email,password=data.get('email'),data.get('password')
    email=email.lower()
    user=db.users_signup.find_one({"email":email})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"message":"Invalid email or password"}),401

    session['user_email'] = email
    print(f"✅ Login successful for {email}")
    return jsonify({"message":"Login successful! Redirect to user dashboard"}),200

# Dashboard route (user section)
@app.route('/user-section', methods=['GET'])
def user_section():
    email = session.get('user_email')
    if not email:
        return jsonify({"message":"Unauthorized"}),401
    user = db.users_signup.find_one({"email":email}, {"_id":0, "password_hash":0})
    return jsonify({"message":"User section data","data":user}),200

# Logout
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message":"Logged out successfully"}),200

if __name__=="__main__":
    app.run(debug=True)
