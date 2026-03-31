from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import db, User, Budget

app = Flask(__name__)
CORS(app)

# PostgreSQL config
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgres@localhost:5433/budget_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "super-secret-key-change-this"

db.init_app(app)
jwt = JWTManager(app)


@app.route("/")
def home():
    return jsonify({"message": "Flask API is running"}), 200


@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "Request body is required"}), 400

        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        if username is None or str(username).strip() == "":
            return jsonify({"message": "Username is required"}), 400

        if email is None or str(email).strip() == "":
            return jsonify({"message": "Email is required"}), 400

        if password is None or str(password).strip() == "":
            return jsonify({"message": "Password is required"}), 400

        username = str(username).strip()
        email = str(email).strip().lower()
        password = str(password).strip()

        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            return jsonify({"message": "Username already exists"}), 409

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return jsonify({"message": "Email already exists"}), 409

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "message": "User registered successfully"
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": "Registration failed",
            "error": str(e)
        }), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "Request body is required"}), 400

        email = data.get("email")
        password = data.get("password")

        if email is None or str(email).strip() == "":
            return jsonify({"message": "Email is required"}), 400

        if password is None or str(password).strip() == "":
            return jsonify({"message": "Password is required"}), 400

        email = str(email).strip().lower()
        password = str(password).strip()

        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({"message": "Invalid email or password"}), 401

        if not check_password_hash(user.password, password):
            return jsonify({"message": "Invalid email or password"}), 401

        token = create_access_token(identity=str(user.id))

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Login failed",
            "error": str(e)
        }), 500


@app.route("/budget", methods=["POST"])
@jwt_required()
def add_budget():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"message": "Request body is required"}), 400

        current_user_id = get_jwt_identity()

        title = data.get("title")
        amount = data.get("amount")
        date = data.get("date")

        if title is None or str(title).strip() == "":
            return jsonify({"message": "Title is required"}), 400

        if amount is None or str(amount).strip() == "":
            return jsonify({"message": "Amount is required"}), 400

        if date is None or str(date).strip() == "":
            return jsonify({"message": "Date is required"}), 400

        title = str(title).strip()
        date = str(date).strip()

        try:
            amount = float(amount)
        except ValueError:
            return jsonify({"message": "Amount must be a number"}), 400

        if amount <= 0:
            return jsonify({"message": "Amount must be greater than 0"}), 400

        new_budget = Budget(
            title=title,
            amount=amount,
            date=date,
            user_id=int(current_user_id)
        )

        db.session.add(new_budget)
        db.session.commit()

        return jsonify({
            "message": "Budget added successfully",
            "budget": {
                "id": new_budget.id,
                "title": new_budget.title,
                "amount": new_budget.amount,
                "date": new_budget.date,
                "user_id": new_budget.user_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": "Failed to add budget",
            "error": str(e)
        }), 500


@app.route("/budget", methods=["GET"])
@jwt_required()
def get_budgets():
    try:
        current_user_id = get_jwt_identity()

        budgets = Budget.query.filter_by(user_id=int(current_user_id)).all()

        if not budgets:
            return jsonify({
                "message": "No budgets found",
                "budgets": []
            }), 200

        budget_list = []

        for budget in budgets:
            budget_list.append({
                "id": budget.id,
                "title": budget.title,
                "amount": budget.amount,
                "date": budget.date,
                "user_id": budget.user_id
            })

        return jsonify({
            "message": "Budgets fetched successfully",
            "budgets": budget_list
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Failed to fetch budgets",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)