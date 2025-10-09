import os, random, re
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

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
    """Generate random numeric OTP"""
    return "".join(str(random.randint(0, 9)) for _ in range(n))


def send_email_otp(to_email, otp):
    """Send OTP email using Gmail securely"""
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

        # Gmail SMTP setup
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())
        server.quit()

        print(f"✅ OTP sent successfully to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication error — check Gmail App Password.")
        return False
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False


# ---------- Routes ----------
@app.route("/test")
def test():
    return jsonify({"message": "Server running"})


@app.route("/signup-request", methods=["POST"])
def signup_request():
    try:
        data = request.get_json()
        name, email, password = data.get("name"), data.get("email"), data.get("password")

        if not all([name, email, password]):
            return jsonify({"message": "Name, email, and password required"}), 400

        # ✅ Strong password rule
        strong_password = re.compile(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$'
        )
        if not strong_password.match(password):
            return jsonify({
                "message": "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character."
            }), 400

        email = email.lower()
        if db.users_signup.find_one({"email": email}):
            return jsonify({"message": "User already exists"}), 400

        # Generate OTP
        otp = gen_otp()
        otp_hash = generate_password_hash(otp)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=OTP_TTL_SECONDS)

        temp_doc = {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "otp_hash": otp_hash,
            "expires_at": expires_at
        }

        db.temp_users.replace_one({"email": email}, temp_doc, upsert=True)

        # Send OTP
        if send_email_otp(email, otp):
            return jsonify({"message": "OTP sent to your email"}), 200
        else:
            return jsonify({"message": "Failed to send OTP"}), 500

    except Exception as e:
        print("signup-request error:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json()
        email, otp = data.get("email"), data.get("otp")
        if not all([email, otp]):
            return jsonify({"message": "Missing fields"}), 400

        email = email.lower()
        temp = db.temp_users.find_one({"email": email})
        if not temp:
            return jsonify({"message": "No pending signup"}), 401

        expires_at = temp["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

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

        session["user_email"] = email
        print(f"✅ Signup complete for {email}")
        return jsonify({"message": "Signup complete! Redirect to avatar"}), 201

    except Exception as e:
        print("verify-otp error:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email, password = data.get("email"), data.get("password")
        email = email.lower()
        user = db.users_signup.find_one({"email": email})
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"message": "Invalid email or password"}), 401

        session["user_email"] = email
        print(f"✅ Login successful for {email}")
        return jsonify({"message": "Login successful! Redirect to user dashboard"}), 200

    except Exception as e:
        print("login error:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500


@app.route("/user-section", methods=["GET"])
def user_section():
    email = session.get("user_email")
    if not email:
        return jsonify({"message": "Unauthorized"}), 401
    user = db.users_signup.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    return jsonify({"message": "User section data", "data": user}), 200


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route("/join-us", methods=["POST"])
def join_us():
    try:
        data = request.get_json() or {}
        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        reason = data.get("reason")
        availability = data.get("availability")
        role = data.get("role")

        if not name or not email or not role:
            return jsonify({"message": "Name, Email and Role are required!"}), 400

        # ✅ Save volunteer data
        db.volunteers.insert_one({
            "name": name,
            "email": email,
            "phone": phone,
            "reason": reason,
            "availability": availability,
            "role": role,
            "joined_at": datetime.now(timezone.utc)
        })

        # ✅ Optional: Send Thank-You Email
        subject = f"Thank you for joining Soulix as {role} 🌿"
        body = f"""
Hello {name},

Thank you for joining the Soulix team as a {role}!

We appreciate your willingness to make a difference.
We’ll reach out to you soon with the next steps.

Warm regards,  
Team Soulix 💙
        """

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = f"Soulix 💙 <{SMTP_USER}>"
            msg["To"] = email

            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [email], msg.as_string())
            server.quit()

            print(f"✅ Volunteer mail sent to {email}")
        except Exception as mail_err:
            print("⚠️ Email not sent:", mail_err)

        return jsonify({"message": "Thank you for joining Soulix! We'll contact you soon."}), 200

    except Exception as e:
        import traceback
        print("join-us error:", e)
        traceback.print_exc()
        return jsonify({"message": "Server error", "error": str(e)}), 500
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        email = data.get("email", None)  # Optional for personalized replies

        if not user_message:
            return jsonify({"message": "No message received"}), 400

        # Check if user exists (personalization)
        user_info = None
        if email:
            user_info = db.users_signup.find_one({"email": email}, {"_id": 0, "password_hash": 0})

        # Build context dynamically
        base_prompt = f"""
You are Serenity 💙 — an empathetic, calm chatbot assistant for Soulix, 
a platform that helps reduce food waste and support well-being.
Always reply in a warm, friendly tone.

If the user seems to be a registered volunteer or member, use their name or role naturally.
If data is available in MongoDB, include it in your reply politely.

Database info:
User info: {user_info or "No data found for this email."}

Your answer should be short (under 80 words), clear, and emotionally intelligent.
"""
        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=250,
            temperature=0.8,
        )

        reply = completion.choices[0].message["content"]
        print(f"🤖 Serenity reply: {reply}")
        return jsonify({"reply": reply}), 200

    except Exception as e:
        print("chat error:", e)
        return jsonify({"message": "Server error", "error": str(e)}), 500

# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
