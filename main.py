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
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app)
load_dotenv()

database_url = os.getenv("DATABASE_URL")
jwt_secret_key = os.getenv("JWT_SECRET_KEY")

if not database_url:
    raise RuntimeError("DATABASE_URL is required in environment variables.")

if not jwt_secret_key:
    raise RuntimeError("JWT_SECRET_KEY is required in environment variables.")

# PostgreSQL config
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = jwt_secret_key

db.init_app(app)
jwt = JWTManager(app)

allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

@app.route("/")
def home():
    return jsonify({"message": "Flask API is running"}), 200


@app.route("/register", methods=allowed_methods)
def register():
    try:
        if request.method == "POST":
                
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
        
        else:
            return jsonify({"message": "Method not allowed"}), 405

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": "Registration failed",
            "error": str(e)
        }), 500


@app.route("/login", methods=allowed_methods)
def login():
    try:
        if request.method == "POST":

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

            token = create_access_token(identity=str(user.email))

            return jsonify({
                "message": "Login successful",
                "token": token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            }), 200

        else:
            return jsonify({"message": "Method not allowed"}), 405
        
    except Exception as e:
        return jsonify({
            "message": "Login failed",
            "error": str(e)
        }), 500


@app.route("/budget", methods=allowed_methods)
@jwt_required()
def add_budget():
    try:
        if request.method == "POST":
                
            data = request.get_json()

            if not data:
                return jsonify({"message": "Request body is required"}), 400

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

            current_user_email = get_jwt_identity()

            current_user = User.query.filter_by(email=current_user_email).first()

            new_budget = Budget(
                title=title,
                amount=amount,
                date=date,
                user_id=current_user.id
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
        
        elif request.method == "GET":
                
            current_user_email = get_jwt_identity()

            current_user = User.query.filter_by(email=current_user_email).first()

            budgets = Budget.query.filter_by(user_id=current_user.id).all()

            if not budgets:
                return jsonify({
                    "message": "No budgets found",
                    "budgets": []
                }), 200

            else:

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

        else:
            return jsonify({"message": "Method not allowed"}), 405

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "message": "Failed to add budget",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)