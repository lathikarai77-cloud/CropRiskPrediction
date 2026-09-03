from flask import Flask, render_template, request, redirect, url_for, session
import joblib
import pandas as pd
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Secret key for login sessions
app.secret_key = "crop-risk-prediction-secret-key-change-this"


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
# LATEST PREDICTION
# =========================================================

latest_prediction = {
    "crop": None,
    "temperature": None,
    "humidity": None,
    "lw": None,
    "prediction": None,
    "disease_risks": [],
    "recommendation": None,
    "alert": None
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    connection = sqlite3.connect("crop_risk.db")

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# CREATE / UPDATE DATABASE
# =========================================================

def create_database():

    connection = sqlite3.connect("crop_risk.db")

    cursor = connection.cursor()

    # =====================================================
    # USERS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            phone TEXT,

            password TEXT NOT NULL,

            created_at TEXT

        )
    """)


    # =====================================================
    # PREDICTIONS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            timestamp TEXT,

            crop TEXT,

            temperature REAL,

            humidity REAL,

            leaf_wetness INTEGER,

            risk_level TEXT,

            disease_risks TEXT,

            recommendation TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(id)

        )
    """)


    # =====================================================
    # NOTIFICATIONS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            message TEXT NOT NULL,

            risk_level TEXT,

            is_read INTEGER DEFAULT 0,

            created_at TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(id)

        )
    """)


    # =====================================================
    # CHECK OLD PREDICTIONS TABLE COLUMNS
    # =====================================================

    cursor.execute(
        "PRAGMA table_info(predictions)"
    )

    columns = [
        column[1]
        for column in cursor.fetchall()
    ]


    # Add user_id to old database
    if "user_id" not in columns:

        cursor.execute("""
            ALTER TABLE predictions
            ADD COLUMN user_id INTEGER
        """)


    # Add crop if missing
    if "crop" not in columns:

        cursor.execute("""
            ALTER TABLE predictions
            ADD COLUMN crop TEXT
        """)


    connection.commit()

    connection.close()


# Create database
create_database()


# =========================================================
# LOGIN CHECK
# =========================================================

def login_required():

    return "user_id" in session


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user():

    if "user_id" not in session:

        return None

    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    connection.close()

    return user


# =========================================================
# DISEASE RISK FUNCTION
# =========================================================

def get_disease_risks(
    crop,
    temperature,
    humidity,
    lw
):

    diseases = []


    # =====================================================
    # GRAPE
    # =====================================================

    if crop == "Grape":

        if 20 <= temperature <= 30 and humidity >= 50:

            diseases.append(
                "Powdery Mildew"
            )


        if humidity >= 70 and lw >= 10:

            diseases.append(
                "Downy Mildew"
            )


        if humidity >= 65 and lw >= 5:

            diseases.append(
                "Bacterial Leaf Spot"
            )


    # =====================================================
    # RICE
    # =====================================================

    elif crop == "Rice":

        if humidity >= 80 and temperature >= 20:

            diseases.append(
                "Rice Blast"
            )


        if temperature >= 25 and humidity >= 60:

            diseases.append(
                "Brown Spot"
            )


        if humidity >= 85 and temperature >= 25:

            diseases.append(
                "Sheath Blight"
            )


    # =====================================================
    # TOMATO
    # =====================================================

    elif crop == "Tomato":

        if humidity >= 70 and temperature >= 20:

            diseases.append(
                "Early Blight"
            )


        if humidity >= 80 and temperature <= 25:

            diseases.append(
                "Late Blight"
            )


        if humidity >= 70 and lw >= 5:

            diseases.append(
                "Bacterial Spot"
            )


    # =====================================================
    # ARECA NUT
    # =====================================================

    elif crop == "Areca Nut":

        if humidity >= 80 and temperature >= 25:

            diseases.append(
                "Fruit Rot"
            )


        if humidity >= 70 and lw >= 5:

            diseases.append(
                "Leaf Spot"
            )


        if temperature >= 25 and humidity >= 70:

            diseases.append(
                "Yellow Leaf Disease"
            )


    # =====================================================
    # CHILLI
    # =====================================================

    elif crop == "Chilli":

        if humidity >= 70 and temperature >= 25:

            diseases.append(
                "Anthracnose"
            )


        if humidity >= 60 and temperature >= 20:

            diseases.append(
                "Powdery Mildew"
            )


        if humidity >= 70 and lw >= 5:

            diseases.append(
                "Leaf Spot"
            )


    # =====================================================
    # POTATO
    # =====================================================

    elif crop == "Potato":

        if humidity >= 70 and temperature >= 20:

            diseases.append(
                "Early Blight"
            )


        if humidity >= 80 and temperature <= 25:

            diseases.append(
                "Late Blight"
            )


    # =====================================================
    # NO DISEASE
    # =====================================================

    if not diseases:

        diseases.append(
            "No major disease risk detected"
        )


    return diseases


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        # =================================================
        # VALIDATION
        # =================================================

        if not name or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all required fields."
            )


        if len(password) < 6:

            return render_template(
                "register.html",
                error="Password must contain at least 6 characters."
            )


        # =================================================
        # CHECK EXISTING USER
        # =================================================

        connection = get_db_connection()

        existing_user = connection.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        if existing_user:

            connection.close()

            return render_template(
                "register.html",
                error="An account with this email already exists."
            )


        # =================================================
        # HASH PASSWORD
        # =================================================

        hashed_password = generate_password_hash(
            password
        )


        # =================================================
        # CREATE USER
        # =================================================

        current_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


        connection.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                phone,
                password,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                phone,
                hashed_password,
                current_time
            )
        )


        connection.commit()

        connection.close()


        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        connection = get_db_connection()


        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        connection.close()


        # =================================================
        # CHECK USER
        # =================================================

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["user_email"] = user["email"]


            return redirect(
                url_for("home")
            )


        return render_template(
            "login.html",
            error="Invalid email or password."
        )


    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# HOME / PREDICTION
# =========================================================

@app.route("/", methods=["GET", "POST"])
def home():

    # =====================================================
    # LOGIN REQUIRED
    # =====================================================

    if not login_required():

        return redirect(
            url_for("login")
        )


    prediction = None

    crop = "Grape"

    recommendation = None

    disease_risks = []

    temperature = None

    humidity = None

    lw = None

    alert = None


    # =====================================================
    # POST REQUEST
    # =====================================================

    if request.method == "POST":

        crop = request.form.get(
            "crop",
            "Grape"
        )


        # =================================================
        # GET INPUT VALUES
        # =================================================

        try:

            temperature = float(
                request.form.get(
                    "temperature",
                    0
                )
            )


            humidity = float(
                request.form.get(
                    "humidity",
                    0
                )
            )


            lw = int(
                request.form.get(
                    "lw",
                    0
                )
            )


        except ValueError:

            alert = (
                "❌ Please enter valid numerical values."
            )


            return render_template(
                "index.html",
                crop=crop,
                crops=SUPPORTED_CROPS,
                prediction=None,
                recommendation=None,
                disease_risks=[],
                temperature=None,
                humidity=None,
                lw=None,
                alert=alert,
                user=get_current_user()
            )


        # =================================================
        # INPUT VALIDATION
        # =================================================

        if crop not in SUPPORTED_CROPS:

            alert = (
                "❌ Please select a valid crop."
            )


            return render_template(
                "index.html",
                crop="Grape",
                crops=SUPPORTED_CROPS,
                prediction=None,
                recommendation=None,
                disease_risks=[],
                temperature=None,
                humidity=None,
                lw=None,
                alert=alert,
                user=get_current_user()
            )


        if temperature < 0 or temperature > 60:

            alert = (
                "❌ Temperature must be "
                "between 0°C and 60°C."
            )


            return render_template(
                "index.html",
                crop=crop,
                crops=SUPPORTED_CROPS,
                prediction=None,
                recommendation=None,
                disease_risks=[],
                temperature=temperature,
                humidity=humidity,
                lw=lw,
                alert=alert,
                user=get_current_user()
            )


        if humidity < 0 or humidity > 100:

            alert = (
                "❌ Humidity must be "
                "between 0% and 100%."
            )


            return render_template(
                "index.html",
                crop=crop,
                crops=SUPPORTED_CROPS,
                prediction=None,
                recommendation=None,
                disease_risks=[],
                temperature=temperature,
                humidity=humidity,
                lw=lw,
                alert=alert,
                user=get_current_user()
            )


        if lw < 0 or lw > 100:

            alert = (
                "❌ Leaf wetness must be "
                "between 0 and 100."
            )


            return render_template(
                "index.html",
                crop=crop,
                crops=SUPPORTED_CROPS,
                prediction=None,
                recommendation=None,
                disease_risks=[],
                temperature=temperature,
                humidity=humidity,
                lw=lw,
                alert=alert,
                user=get_current_user()
            )


        # =================================================
        # PREPARE INPUT DATA
        # =================================================

        input_data = pd.DataFrame({

            "Temperature": [
                temperature
            ],

            "Humidity": [
                humidity
            ],

            "LW": [
                lw
            ]

        })


        # =================================================
        # ML PREDICTION
        # =================================================

        prediction = model.predict(
            input_data
        )[0]


        # =================================================
        # DISEASE RISKS
        # =================================================

        disease_risks = get_disease_risks(
            crop,
            temperature,
            humidity,
            lw
        )


        # =================================================
        # RECOMMENDATION
        # =================================================

        if prediction == "High":

            recommendation = (
                f"Environmental conditions indicate a "
                f"high disease risk for {crop}. "
                f"Monitor the crop closely and take "
                f"appropriate preventive measures."
            )

        elif prediction == "Medium":

            recommendation = (
                f"Environmental conditions indicate a "
                f"moderate disease risk for {crop}. "
                f"Continue monitoring the crop and "
                f"environmental conditions."
            )

        else:

            recommendation = (
                f"Environmental conditions indicate a "
                f"low disease risk for {crop}. "
                f"Continue regular crop monitoring."
            )


        # =================================================
        # RISK ALERT
        # =================================================

        if prediction == "High":

            alert = (
                "🚨 HIGH DISEASE RISK DETECTED! "
                "Immediate preventive action is recommended."
            )

        elif prediction == "Medium":

            alert = (
                "⚠️ MODERATE DISEASE RISK. "
                "Continue monitoring the crop."
            )

        else:

            alert = (
                "✅ LOW DISEASE RISK. "
                "Continue regular crop monitoring."
            )


        # =================================================
        # STORE LATEST PREDICTION
        # =================================================

        latest_prediction["crop"] = crop

        latest_prediction["temperature"] = temperature

        latest_prediction["humidity"] = humidity

        latest_prediction["lw"] = lw

        latest_prediction["prediction"] = prediction

        latest_prediction["disease_risks"] = disease_risks

        latest_prediction["recommendation"] = recommendation

        latest_prediction["alert"] = alert


        # =================================================
        # SAVE PREDICTION
        # =================================================

        connection = get_db_connection()


        current_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


        disease_text = ", ".join(
            disease_risks
        )


        connection.execute(
            """
            INSERT INTO predictions
            (
                user_id,
                timestamp,
                crop,
                temperature,
                humidity,
                leaf_wetness,
                risk_level,
                disease_risks,
                recommendation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                current_time,
                crop,
                temperature,
                humidity,
                lw,
                prediction,
                disease_text,
                recommendation
            )
        )


        # =================================================
        # CREATE NOTIFICATION
        # =================================================

        if prediction == "High":

            notification_title = (
                "🚨 High Disease Risk"
            )

            notification_message = (
                f"High disease risk detected "
                f"for your {crop} crop. "
                f"Immediate preventive action "
                f"is recommended."
            )


        elif prediction == "Medium":

            notification_title = (
                "⚠️ Moderate Disease Risk"
            )

            notification_message = (
                f"Moderate disease risk detected "
                f"for your {crop} crop. "
                f"Please continue monitoring."
            )


        else:

            notification_title = None

            notification_message = None


        if notification_title:

            connection.execute(
                """
                INSERT INTO notifications
                (
                    user_id,
                    title,
                    message,
                    risk_level,
                    is_read,
                    created_at
                )
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (
                    session["user_id"],
                    notification_title,
                    notification_message,
                    prediction,
                    current_time
                )
            )


        connection.commit()

        connection.close()


    # =====================================================
    # RENDER HOME
    # =====================================================

    return render_template(
        "index.html",

        crop=crop,

        crops=SUPPORTED_CROPS,

        prediction=prediction,

        recommendation=recommendation,

        disease_risks=disease_risks,

        temperature=temperature,

        humidity=humidity,

        lw=lw,

        alert=alert,

        user=get_current_user()
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    # =====================================================
    # LOGIN REQUIRED
    # =====================================================

    if not login_required():

        return redirect(
            url_for("login")
        )


    # =====================================================
    # READ CSV DATASET
    # =====================================================

    data = pd.read_csv(
        "dataset/risk_labeled_grape_data.csv"
    )


    recent_data = data.tail(100)


    temperature = (
        recent_data["Temperature"].tolist()
    )


    humidity = (
        recent_data["Humidity"].tolist()
    )


    leaf_wetness = (
        recent_data["LW"].tolist()
    )


    # =====================================================
    # CONNECT DATABASE
    # =====================================================

    connection = get_db_connection()


    cursor = connection.cursor()


    user_id = session["user_id"]


    # =====================================================
    # PREDICTION HISTORY
    # =====================================================

    cursor.execute(
        """
        SELECT *
        FROM predictions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,)
    )


    prediction_history = cursor.fetchall()


    # =====================================================
    # LATEST PREDICTION VALUES
    # =====================================================

    latest_temperature = None

    latest_humidity = None

    latest_leaf_wetness = None

    latest_crop = None


    if prediction_history:

        latest_temperature = (
            prediction_history[0]["temperature"]
        )

        latest_humidity = (
            prediction_history[0]["humidity"]
        )

        latest_leaf_wetness = (
            prediction_history[0]["leaf_wetness"]
        )

        latest_crop = (
            prediction_history[0]["crop"]
        )


    # =====================================================
    # RISK TREND
    # =====================================================

    cursor.execute(
        """
        SELECT timestamp, risk_level
        FROM predictions
        WHERE user_id = ?
        ORDER BY id ASC
        LIMIT 20
        """,
        (user_id,)
    )


    risk_history_rows = cursor.fetchall()


    risk_history = [
        dict(row)
        for row in risk_history_rows
    ]


    # =====================================================
    # RISK SUMMARY
    # =====================================================

    cursor.execute(
        """
        SELECT risk_level, COUNT(*) AS count
        FROM predictions
        WHERE user_id = ?
        GROUP BY risk_level
        """,
        (user_id,)
    )


    risk_summary_rows = cursor.fetchall()


    risk_summary = {

        "Low": 0,

        "Medium": 0,

        "High": 0

    }


    for row in risk_summary_rows:

        risk_summary[
            row["risk_level"]
        ] = row["count"]


    # =====================================================
    # CROP-WISE RISK SUMMARY
    # =====================================================

    cursor.execute(
        """
        SELECT
            COALESCE(crop, 'Unknown') AS crop,
            risk_level,
            COUNT(*) AS count

        FROM predictions

        WHERE user_id = ?

        GROUP BY crop, risk_level

        ORDER BY crop
        """,
        (user_id,)
    )


    crop_risk_rows = cursor.fetchall()


    crop_risk_summary = {}


    for row in crop_risk_rows:

        crop_name = row["crop"]

        risk_level = row["risk_level"]

        count = row["count"]


        if crop_name not in crop_risk_summary:

            crop_risk_summary[crop_name] = {

                "Total": 0,

                "Low": 0,

                "Medium": 0,

                "High": 0

            }


        crop_risk_summary[
            crop_name
        ][risk_level] = count


        crop_risk_summary[
            crop_name
        ]["Total"] += count


    # =====================================================
    # CROP-WISE CHART DATA
    # =====================================================

    crop_chart_labels = list(
        crop_risk_summary.keys()
    )


    crop_low_values = [

        risks["Low"]

        for risks
        in crop_risk_summary.values()

    ]


    crop_medium_values = [

        risks["Medium"]

        for risks
        in crop_risk_summary.values()

    ]


    crop_high_values = [

        risks["High"]

        for risks
        in crop_risk_summary.values()

    ]


    # =====================================================
    # DISEASE MONITORING
    # =====================================================

    cursor.execute(
        """
        SELECT disease_risks

        FROM predictions

        WHERE user_id = ?
        """,
        (user_id,)
    )


    disease_rows = cursor.fetchall()


    disease_summary = {}


    for row in disease_rows:

        diseases = row["disease_risks"]


        if diseases:

            disease_list = [

                disease.strip()

                for disease
                in diseases.split(",")

            ]


            for disease in disease_list:

                if (
                    disease
                    and
                    disease !=
                    "No major disease risk detected"
                ):

                    if disease not in disease_summary:

                        disease_summary[disease] = 0


                    disease_summary[disease] += 1


    # =====================================================
    # HIGH-RISK ALERTS
    # =====================================================

    cursor.execute(
        """
        SELECT
            timestamp,
            crop,
            temperature,
            humidity,
            leaf_wetness,
            risk_level,
            disease_risks

        FROM predictions

        WHERE user_id = ?

        AND risk_level = 'High'

        ORDER BY id DESC

        LIMIT 5
        """,
        (user_id,)
    )


    high_risk_alerts = cursor.fetchall()


    # =====================================================
    # NOTIFICATIONS
    # =====================================================

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


    # =====================================================
    # UNREAD NOTIFICATIONS
    # =====================================================

    cursor.execute(
        """
        SELECT COUNT(*) AS count

        FROM notifications

        WHERE user_id = ?

        AND is_read = 0
        """,
        (user_id,)
    )


    unread_notifications = cursor.fetchone()["count"]


    # =====================================================
    # RISK LABELS
    # =====================================================

    risk_labels = [
        "Low",
        "Medium",
        "High"
    ]


    risk_values = [

        risk_summary["Low"],

        risk_summary["Medium"],

        risk_summary["High"]

    ]


    # =====================================================
    # CLOSE DATABASE
    # =====================================================

    connection.close()


    # =====================================================
    # ML MODEL PERFORMANCE
    # =====================================================

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


    # =====================================================
    # DASHBOARD
    # =====================================================

    return render_template(

        "dashboard.html",

        temperature=temperature,

        humidity=humidity,

        leaf_wetness=leaf_wetness,

        latest_temperature=latest_temperature,

        latest_humidity=latest_humidity,

        latest_leaf_wetness=latest_leaf_wetness,

        latest_crop=latest_crop,

        risk_labels=risk_labels,

        risk_values=risk_values,

        latest=latest_prediction,

        prediction_history=prediction_history,

        risk_history=risk_history,

        risk_summary=risk_summary,

        disease_summary=disease_summary,

        high_risk_alerts=high_risk_alerts,

        crop_risk_summary=crop_risk_summary,

        crop_chart_labels=crop_chart_labels,

        crop_low_values=crop_low_values,

        crop_medium_values=crop_medium_values,

        crop_high_values=crop_high_values,

        notifications=notifications,

        unread_notifications=unread_notifications,

        user=get_current_user(),

        model_accuracy=model_accuracy,

        model_metrics=model_metrics,

        feature_importance=feature_importance

    )


# =========================================================
# MARK NOTIFICATIONS AS READ
# =========================================================

@app.route("/notifications/read")
def mark_notifications_read():

    if not login_required():

        return redirect(
            url_for("login")
        )


    connection = get_db_connection()


    connection.execute(
        """
        UPDATE notifications

        SET is_read = 1

        WHERE user_id = ?
        """,
        (session["user_id"],)
    )


    connection.commit()

    connection.close()


    return redirect(
        url_for("dashboard")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )