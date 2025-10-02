from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId

app = Flask(__name__)
CORS(app)

# MongoDB connection (fixed URL encoding)
app.config["MONGO_URI"] = "mongodb+srv://aditisundaram35_db_user:Aditi2005%23%23@soulix.hq20ejt.mongodb.net/SoulixDB"
mongo = PyMongo(app)

# Test route
@app.route("/test")
def test():
    return "Server is running!"

# Signup
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"message": "All fields are required!"}), 400

    if mongo.db.users.find_one({"email": email}):
        return jsonify({"message": "User already exists!"}), 400

    hashed_password = generate_password_hash(password)
    user_id = mongo.db.users.insert_one({
        "name": name,
        "email": email,
        "password": hashed_password
    }).inserted_id

    user = mongo.db.users.find_one({"_id": user_id})
    return jsonify({
        "message": "User created successfully!",
        "user": {"_id": str(user["_id"]), "name": user["name"], "email": user["email"]}
    }), 201

# All users (DEV)
@app.route("/all-users", methods=["GET"])
def all_users():
    users = mongo.db.users.find({}, {"password": 0})
    output = []
    for user in users:
        output.append({
            "_id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "avatar": user.get("avatar", "")
        })
    return jsonify({"users": output})

# Generate avatar
@app.route("/generate-avatar", methods=["POST"])
def generate_avatar():
    data = request.get_json()
    user_id = data.get("user_id")
    avatar_url = f"https://via.placeholder.com/256.png?text=Avatar+{user_id}"
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"avatar": avatar_url}}
    )
    return jsonify({"message": "Avatar generated!", "avatar_url": avatar_url})

if __name__ == "__main__":
    app.run(debug=True)
