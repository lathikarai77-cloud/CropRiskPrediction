from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import joblib
import pandas as pd
import sqlite3
from datetime import datetime

app = Flask(__name__)

# =========================================================

# FLASK SECRET KEY

# =========================================================

app.secret_key = "crop-risk-secret-key-change-later"

# =========================================================

# SUPPORTED CROPS

# =========================================================

SUPPORTED_CROPS = [
"Grape",
"Rice",
"Tomato",
"Areca Nut",
"Chilli",
"Potato"
]

# =========================================================

# LOAD ML MODEL

# =========================================================

model = joblib.load("environmental_risk_model.pkl")

# =========================================================

# DATABASE CONNECTION

# =========================================================

def get_db_connection():
 connection = sqlite3.connect("crop_risk.db")
 connection.row_factory = sqlite3.Row
 return connection

# =========================================================
# CREATE DATABASE TABLES
# =========================================================

def create_database():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            crop TEXT,
            temperature REAL,
            humidity REAL,
            leaf_wetness INTEGER,
            risk_level TEXT,
            disease_risks TEXT,
            recommendation TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(predictions)")
    columns = [column[1] for column in cursor.fetchall()]

    if "crop" not in columns:
        cursor.execute("""
            ALTER TABLE predictions
            ADD COLUMN crop TEXT
        """)

    if "user_id" not in columns:
        cursor.execute("""
            ALTER TABLE predictions
            ADD COLUMN user_id INTEGER
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prediction_id INTEGER,
            message TEXT NOT NULL,
            risk_level TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # SMART IRRIGATION / WATER PUMP TABLE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS irrigation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            crop TEXT NOT NULL,
            soil_moisture REAL DEFAULT 0,
            water_status TEXT DEFAULT 'LOW',
            pump_status TEXT DEFAULT 'OFF',
            auto_mode INTEGER DEFAULT 1,
            updated_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


create_database()

# =========================================================

# LOGIN REQUIRED DECORATOR

# =========================================================

def login_required(function):


 @wraps(function)
 def decorated_function(*args, **kwargs):

    if "user_id" not in session:
        return redirect(url_for("login"))

    return function(*args, **kwargs)

 return decorated_function

# =========================================================
# DISEASE RISK FUNCTION
# =========================================================

def get_disease_risks(crop, temperature, humidity, leaf_wetness):

    diseases = []

    if crop == "Grape":

        if 20 <= temperature <= 30 and humidity >= 50:
            diseases.append("Powdery Mildew")

        if humidity >= 70 and leaf_wetness >= 10:
            diseases.append("Downy Mildew")

        if humidity >= 65 and leaf_wetness >= 5:
            diseases.append("Bacterial Leaf Spot")

    elif crop == "Rice":

        if humidity >= 80 and temperature >= 20:
            diseases.append("Rice Blast")

        if temperature >= 25 and humidity >= 60:
            diseases.append("Brown Spot")

        if humidity >= 85 and temperature >= 25:
            diseases.append("Sheath Blight")

    elif crop == "Tomato":

        if humidity >= 70 and temperature >= 20:
            diseases.append("Early Blight")

        if humidity >= 80 and temperature <= 25:
            diseases.append("Late Blight")

        if humidity >= 70 and leaf_wetness >= 5:
            diseases.append("Bacterial Spot")

    elif crop == "Areca Nut":

        if humidity >= 80 and temperature >= 25:
            diseases.append("Fruit Rot")

        if humidity >= 70 and leaf_wetness >= 5:
            diseases.append("Leaf Spot")

        if temperature >= 25 and humidity >= 70:
            diseases.append("Yellow Leaf Disease")

    elif crop == "Chilli":

        if humidity >= 70 and temperature >= 25:
            diseases.append("Anthracnose")

        if humidity >= 60 and temperature >= 20:
            diseases.append("Powdery Mildew")

        if humidity >= 70 and leaf_wetness >= 5:
            diseases.append("Leaf Spot")

    elif crop == "Potato":

        if humidity >= 70 and temperature >= 20:
            diseases.append("Early Blight")

        if humidity >= 80 and temperature <= 25:
            diseases.append("Late Blight")

    if not diseases:
        diseases.append("No major disease risk detected")

    return diseases


# =========================================================
# RECOMMENDATION
# =========================================================

def get_recommendation(risk_level, crop):

    if risk_level == "High":

        return (
            f"🚨 HIGH RISK: Immediate preventive action is recommended "
            f"for {crop}. Inspect plants, improve air circulation, "
            f"and take suitable disease-control measures."
        )

    elif risk_level == "Medium":

        return (
            f"⚠️ MEDIUM RISK: Monitor the {crop} plants closely. "
            f"Check leaves regularly and maintain proper irrigation "
            f"and ventilation."
        )

    else:

        return (
            f"✅ LOW RISK: Conditions are currently favorable for "
            f"{crop}. Continue regular monitoring."
        )


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/", methods=["GET", "POST"])
@login_required
def home():

    prediction = None

    if request.method == "POST":

        crop = request.form.get("crop")

        temperature = float(request.form.get("temperature"))
        humidity = float(request.form.get("humidity"))
        leaf_wetness = int(request.form.get("leaf_wetness"))

        # ML prediction
        input_data = pd.DataFrame(
            [[temperature, humidity, leaf_wetness]],
            columns=["Temperature", "Humidity", "LW"]
        )

        risk_level = model.predict(input_data)[0]

        # Disease prediction
        disease_risks = get_disease_risks(
            crop,
            temperature,
            humidity,
            leaf_wetness
        )

        # Recommendation
        recommendation = get_recommendation(
            risk_level,
            crop
        )

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        # Save prediction for logged-in user
        cursor.execute(
            """
            INSERT INTO predictions
            (
                timestamp,
                crop,
                temperature,
                humidity,
                leaf_wetness,
                risk_level,
                disease_risks,
                recommendation,
                user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                crop,
                temperature,
                humidity,
                leaf_wetness,
                risk_level,
                ", ".join(disease_risks),
                recommendation,
                session["user_id"]
            )
        )

        prediction_id = cursor.lastrowid

        # Create notification for Medium/High risk
        if risk_level in ["High", "Medium"]:

            if risk_level == "High":

                message = (
                    f"🚨 High disease risk detected for {crop}!"
                )

            else:

                message = (
                    f"⚠️ Medium disease risk detected for {crop}."
                )

            cursor.execute(
                """
                INSERT INTO notifications
                (
                    user_id,
                    prediction_id,
                    message,
                    risk_level,
                    is_read,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    prediction_id,
                    message,
                    risk_level,
                    0,
                    timestamp
                )
            )

        connection.commit()
        connection.close()

        prediction = {
            "crop": crop,
            "temperature": temperature,
            "humidity": humidity,
            "leaf_wetness": leaf_wetness,
            "risk_level": risk_level,
            "disease_risks": disease_risks,
            "recommendation": recommendation
        }

    return render_template(
        "index.html",
        prediction=prediction,
        user_name=session.get("user_name"),
        crops=SUPPORTED_CROPS,
        crop=request.form.get("crop", "Grape") if request.method == "POST" else "Grape",
        temperature=request.form.get("temperature") if request.method == "POST" else None,
        humidity=request.form.get("humidity") if request.method == "POST" else None,
        leaf_wetness=request.form.get("leaf_wetness") if request.method == "POST" else None
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # User predictions
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM predictions
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    )

    predictions = cursor.fetchall()

    # -----------------------------------------------------
    # Latest prediction
    # -----------------------------------------------------

    latest_prediction = None

    if predictions:

        latest_prediction = predictions[0]

    # -----------------------------------------------------
    # Risk summary
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT risk_level, COUNT(*) AS count
        FROM predictions
        WHERE user_id = ?
        GROUP BY risk_level
        """,
        (user_id,)
    )

    risk_summary = cursor.fetchall()

    # -----------------------------------------------------
    # Crop-wise risk
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT crop, risk_level, COUNT(*) AS count
        FROM predictions
        WHERE user_id = ?
        GROUP BY crop, risk_level
        """,
        (user_id,)
    )

    crop_risk = cursor.fetchall()

    # -----------------------------------------------------
    # Disease monitoring
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT disease_risks, COUNT(*) AS count
        FROM predictions
        WHERE user_id = ?
        GROUP BY disease_risks
        """,
        (user_id,)
    )

    disease_summary = cursor.fetchall()

    # -----------------------------------------------------
    # Notifications
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (user_id,)
    )

    notifications = cursor.fetchall()

    # -----------------------------------------------------
    # Unread notification count
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM notifications
        WHERE user_id = ?
        AND is_read = 0
        """,
        (user_id,)
    )

    unread_count = cursor.fetchone()["count"]

    # -----------------------------------------------------
    # High-risk alerts
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM predictions
        WHERE user_id = ?
        AND risk_level = 'High'
        ORDER BY id DESC
        LIMIT 10
        """,
        (user_id,)
    )

    high_risk_alerts = cursor.fetchall()

    connection.close()

    # -----------------------------------------------------
    # Dataset for environment charts
    # -----------------------------------------------------

    try:

        data = pd.read_csv(
            "dataset/risk_labeled_grape_data.csv"
        )

        recent_data = data.tail(100)

        temperature_data = recent_data[
            "Temperature"
        ].tolist()

        humidity_data = recent_data[
            "Humidity"
        ].tolist()

        leaf_wetness_data = recent_data[
            "LW"
        ].tolist()

    except Exception:

        temperature_data = []
        humidity_data = []
        leaf_wetness_data = []

    # -----------------------------------------------------
    # Model information
    # -----------------------------------------------------

    model_accuracy = 99.95

    model_metrics = {
        "High": {
            "precision": 1.00,
            "recall": 1.00,
            "f1": 1.00
        },

        "Low": {
            "precision": 0.97,
            "recall": 1.00,
            "f1": 0.99
        },

        "Medium": {
            "precision": 1.00,
            "recall": 1.00,
            "f1": 1.00
        }
    }

    feature_importance = {
        "Temperature": 0.3206,
        "Humidity": 0.3246,
        "Leaf Wetness": 0.3548
    }

    return render_template(
        "dashboard.html",
        predictions=predictions,
        latest_prediction=latest_prediction,
        risk_summary=risk_summary,
        crop_risk=crop_risk,
        disease_summary=disease_summary,
        notifications=notifications,
        unread_count=unread_count,
        high_risk_alerts=high_risk_alerts,
        temperature_data=temperature_data,
        humidity_data=humidity_data,
        leaf_wetness_data=leaf_wetness_data,
        model_accuracy=model_accuracy,
        model_metrics=model_metrics,
        feature_importance=feature_importance,
        user_name=session.get("user_name")
    )


# =========================================================
# MARK NOTIFICATION AS READ
# =========================================================

@app.route("/notification/read/<int:notification_id>")
@login_required
def mark_notification_read(notification_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE id = ?
        AND user_id = ?
        """,
        (
            notification_id,
            session["user_id"]
        )
    )

    connection.commit()
    connection.close()

    return redirect(url_for("dashboard"))

# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template(
                "register.html",
                error="Please fill all fields."
            )

        password_hash = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    password_hash,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

            connection.commit()
            connection.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            connection.close()

            return render_template(
                "register.html",
                error="Email already registered."
            )

    # IMPORTANT:
    # This handles GET /register
    return render_template("register.html")

# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        )

        user = cursor.fetchone()

        connection.close()

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")

# =========================================================
# SMART IRRIGATION
# =========================================================

@app.route("/irrigation")
@login_required
def irrigation():

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM irrigation
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    irrigation_data = cursor.fetchone()

    connection.close()

    return render_template(
        "irrigation.html",
        irrigation=irrigation_data,
        user_name=session.get("user_name")
    )


# =========================================================
# TURN OFF WATER PUMP
# =========================================================

@app.route("/pump/off", methods=["POST"])
@login_required
def pump_off():

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE irrigation
        SET pump_status = 'OFF',
            updated_at = ?
        WHERE user_id = ?
        """,
        (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            user_id
        )
    )

    connection.commit()
    connection.close()

    return redirect(url_for("irrigation"))


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":
    create_database()

    import os

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )