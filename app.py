# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import joblib
import pandas as pd
import sqlite3
import os
import threading
import time
import uuid
import numpy as np
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import load_img, img_to_array
from datetime import datetime

app = Flask(__name__)

# ============================================================
# POTATO DISEASE IMAGE DETECTION CONFIGURATION
# ============================================================

DISEASE_MODEL_PATH = os.path.join(
    "disease_model",
    "potato_disease_efficientnet.keras"
)

DISEASE_CLASS_PATH = os.path.join(
    "disease_model",
    "potato_class_names_efficientnet.txt"
)

UPLOAD_FOLDER = os.path.join(
    "static",
    "uploads"
)

ALLOWED_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load Potato disease model
disease_model = load_model(DISEASE_MODEL_PATH)

# Load class names
with open(DISEASE_CLASS_PATH, "r") as file:
    DISEASE_CLASSES = [
        line.strip()
        for line in file
        if line.strip()
    ]

print("🥔 Potato disease model loaded successfully.")
print("🌱 Disease classes:", DISEASE_CLASSES)

# ============================================================
# POTATO DISEASE IMAGE PREDICTION
# ============================================================

def predict_potato_disease(image_path):

    # Load image
    image = load_img(
        image_path,
        target_size=(224, 224)
    )

    # Convert image to array
    image_array = img_to_array(image)

    # Add batch dimension
    image_array = np.expand_dims(
        image_array,
        axis=0
    )

    # EfficientNetB0 preprocessing
    # Do NOT use the old MobileNetV2 [-1, 1] normalization.
    # EfficientNetB0 includes its preprocessing internally.

    # Make prediction
    predictions = disease_model.predict(
        image_array,
        verbose=0
    )

    # Get highest probability class
    predicted_index = np.argmax(
        predictions[0]
    )

    confidence = float(
        predictions[0][predicted_index] * 100
    )

    predicted_class = DISEASE_CLASSES[
        predicted_index
    ]

    return predicted_class, confidence

# ============================================================
# POTATO DISEASE INFORMATION
# ============================================================

POTATO_DISEASE_INFO = {
    "healthy": {
        "name": "Healthy Potato Leaf",
        "description": "The AI did not detect visible symptoms of Early Blight or Late Blight in the uploaded image.",
        "recommendation": "Continue regular crop monitoring and maintain proper irrigation and field hygiene."
    },

    "early_blight": {
        "name": "Potato Early Blight",
        "description": "The image shows visual patterns associated with Early Blight.",
        "recommendation": "Inspect nearby plants for similar symptoms, remove severely affected leaves where appropriate, and monitor the crop closely."
    },

    "late_blight": {
        "name": "Potato Late Blight",
        "description": "The image shows visual patterns associated with Late Blight.",
        "recommendation": "Inspect surrounding plants immediately and monitor environmental conditions and disease spread closely."
    }
}

# =========================================================

# FLASK SECRET KEY

# =========================================================

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-this")

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
# CROP ACTIVITY SCHEDULE
# =========================================================

CROP_ACTIVITIES = {

    "Grape": [
        ("07:00 AM", "Check soil moisture and irrigation needs."),
        ("10:00 AM", "Inspect leaves and fruits for disease symptoms."),
        ("05:00 PM", "Check for pest or disease alerts."),
        ("07:00 PM", "Review today's crop health and notifications.")
    ],

    "Rice": [
        ("07:00 AM", "Check water level in the field."),
        ("10:00 AM", "Inspect plants for Rice Blast and Brown Spot symptoms."),
        ("05:00 PM", "Check for pests and disease warnings."),
        ("07:00 PM", "Review crop condition and notifications.")
    ],

    "Tomato": [
        ("07:00 AM", "Check soil moisture and irrigation needs."),
        ("10:00 AM", "Inspect leaves and fruits for disease symptoms."),
        ("05:00 PM", "Check for pests and Bacterial Spot symptoms."),
        ("07:00 PM", "Review crop health and notifications.")
    ],

    "Areca Nut": [
        ("07:00 AM", "Check soil moisture around the plants."),
        ("10:00 AM", "Inspect leaves for spots or yellowing."),
        ("05:00 PM", "Check for Fruit Rot and pest warnings."),
        ("07:00 PM", "Review crop condition and notifications.")
    ],

    "Chilli": [
        ("07:00 AM", "Check soil moisture and irrigation needs."),
        ("10:00 AM", "Inspect leaves and fruits for Anthracnose symptoms."),
        ("05:00 PM", "Check for pests and disease alerts."),
        ("07:00 PM", "Review crop health and notifications.")
    ],

    "Potato": [
        ("07:00 AM", "Check soil moisture and irrigation needs."),
        ("10:00 AM", "Inspect leaves for Early Blight or Late Blight symptoms."),
        ("05:00 PM", "Check for pest and disease warnings."),
        ("07:00 PM", "Review crop condition and notifications.")
    ]
}

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
# ACTIVITY LOG FUNCTION
# =========================================================

def log_activity(user_id, activity, details=""):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO activity_logs
        (
            user_id,
            activity,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            activity,
            details,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    connection.commit()
    connection.close()

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
            created_at TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)

    # -----------------------------------------------------
    # ADD ADMIN FIELD TO USERS TABLE
    # -----------------------------------------------------

    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in cursor.fetchall()]

    if "is_admin" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN is_admin INTEGER DEFAULT 0
        """)

    # -----------------------------------------------------
    # ADD ACTIVE STATUS TO USERS TABLE
    # -----------------------------------------------------

    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in cursor.fetchall()]

    if "is_active" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN is_active INTEGER DEFAULT 1
        """)

    # ADD CROP TO USERS
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in cursor.fetchall()]

    if "crop" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN crop TEXT DEFAULT 'Grape'
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
    # USER ACTIVITY LOG
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity TEXT NOT NULL,
            details TEXT,
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

def admin_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT is_admin FROM users WHERE id = ?",
            (session["user_id"],)
        )

        user = cursor.fetchone()

        connection.close()

        if not user or user["is_admin"] != 1:
            return "Access Denied: Admins only", 403

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

# ============================================================
# POTATO DISEASE DETECTION PAGE
# ============================================================

@app.route("/disease-detection", methods=["GET", "POST"])
@login_required
def disease_detection():

    prediction = None
    confidence = None
    image_url = None
    disease_info = None
    error = None

    # Environmental information
    environmental_data = None
    combined_recommendation = None

    if request.method == "POST":

        # Check whether image was submitted
        if "disease_image" not in request.files:
            error = "Please select a potato leaf image."

            return render_template(
                "disease_detection.html",
                prediction=prediction,
                confidence=confidence,
                image_url=image_url,
                disease_info=disease_info,
                error=error,
                environmental_data=environmental_data,
                combined_recommendation=combined_recommendation
            )

        image = request.files["disease_image"]

        # Check filename
        if image.filename == "":
            error = "Please select an image."

            return render_template(
                "disease_detection.html",
                prediction=prediction,
                confidence=confidence,
                image_url=image_url,
                disease_info=disease_info,
                error=error,
                environmental_data=environmental_data,
                combined_recommendation=combined_recommendation
            )

        # Check extension
        extension = image.filename.rsplit(".", 1)[-1].lower()

        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            error = "Only JPG, JPEG and PNG images are allowed."

            return render_template(
                "disease_detection.html",
                prediction=prediction,
                confidence=confidence,
                image_url=image_url,
                disease_info=disease_info,
                error=error,
                environmental_data=environmental_data,
                combined_recommendation=combined_recommendation
            )

        # Create unique filename
        filename = secure_filename(
            f"{uuid.uuid4().hex}.{extension}"
        )

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        # Save image
        image.save(filepath)

        try:

            # ------------------------------------------------
            # IMAGE AI PREDICTION
            # ------------------------------------------------

            prediction, confidence = predict_potato_disease(
                filepath
            )

            # Get disease information
            disease_info = POTATO_DISEASE_INFO.get(
                prediction,
                {
                    "name": prediction.replace("_", " ").title(),
                    "description": "The AI analyzed the uploaded image.",
                    "recommendation": "Continue monitoring the crop."
                }
            )

            # Image URL for webpage
            image_url = url_for(
                "static",
                filename=f"uploads/{filename}"
            )

            # ------------------------------------------------
            # GET LATEST ENVIRONMENTAL DATA
            # ------------------------------------------------

            connection = get_db_connection()
            cursor = connection.cursor()

            user_id = session["user_id"]

            cursor.execute(
                """
                SELECT
                    crop,
                    temperature,
                    humidity,
                    leaf_wetness,
                    risk_level,
                    recommendation
                FROM predictions
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,)
            )

            latest_prediction = cursor.fetchone()

            connection.close()

            # ------------------------------------------------
            # PREPARE ENVIRONMENTAL DATA
            # ------------------------------------------------

            if latest_prediction:

                environmental_data = {
                    "crop": latest_prediction["crop"],
                    "temperature": latest_prediction["temperature"],
                    "humidity": latest_prediction["humidity"],
                    "leaf_wetness": latest_prediction["leaf_wetness"],
                    "risk_level": latest_prediction["risk_level"],
                    "recommendation": latest_prediction["recommendation"]
                }

                # ------------------------------------------------
                # COMBINED RECOMMENDATION
                # ------------------------------------------------

                if prediction == "healthy":

                    if latest_prediction["risk_level"] == "High":

                        combined_recommendation = (
                            "The image appears healthy, but the current "
                            "environmental conditions indicate HIGH crop "
                            "risk. Continue close monitoring and inspect "
                            "nearby plants regularly."
                        )

                    elif latest_prediction["risk_level"] == "Medium":

                        combined_recommendation = (
                            "The image appears healthy, but environmental "
                            "conditions indicate MEDIUM crop risk. "
                            "Continue regular monitoring."
                        )

                    else:

                        combined_recommendation = (
                            "The image appears healthy and the current "
                            "environmental risk is LOW. Continue regular "
                            "crop monitoring and good field management."
                        )

                else:

                    if latest_prediction["risk_level"] == "High":

                        combined_recommendation = (
                            f"Visible signs associated with "
                            f"{disease_info['name']} were detected and "
                            f"the environmental risk is HIGH. Inspect "
                            f"nearby plants and monitor the crop closely."
                        )

                    elif latest_prediction["risk_level"] == "Medium":

                        combined_recommendation = (
                            f"Visible signs associated with "
                            f"{disease_info['name']} were detected. "
                            f"The environmental risk is MEDIUM. "
                            f"Inspect nearby plants and continue "
                            f"close monitoring."
                        )

                    else:

                        combined_recommendation = (
                            f"Visible signs associated with "
                            f"{disease_info['name']} were detected. "
                            f"The current environmental risk is LOW, "
                            f"but the affected plant should still be "
                            f"monitored carefully."
                        )

            else:

                combined_recommendation = (
                    "No environmental prediction is available yet. "
                    "Run environmental monitoring first to obtain "
                    "a combined crop analysis."
                )

        except Exception as e:

            print("❌ Disease prediction error:", e)

            error = (
                "Unable to analyze the image. "
                "Please try another clear potato leaf image."
            )

    return render_template(
        "disease_detection.html",
        prediction=prediction,
        confidence=confidence,
        image_url=image_url,
        disease_info=disease_info,
        error=error,
        environmental_data=environmental_data,
        combined_recommendation=combined_recommendation
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

    # =========================================================
    # GET FARMER'S CURRENT ASSIGNED CROP
    # =========================================================

    cursor.execute(
        """
        SELECT crop
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    user_crop_row = cursor.fetchone()

    if user_crop_row and user_crop_row["crop"]:
        user_crop = user_crop_row["crop"]
    else:
        user_crop = "Grape"


    # =========================================================
    # USER PREDICTIONS
    # =========================================================

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


    # =========================================================
    # LATEST PREDICTION
    # =========================================================

    latest_prediction = None

    if predictions:
        latest_prediction = predictions[0]


    # =========================================================
    # RISK SUMMARY
    # CURRENT ASSIGNED CROP ONLY
    # =========================================================

    cursor.execute(
        """
        SELECT risk_level, COUNT(*) AS count
        FROM predictions
        WHERE user_id = ?
        AND crop = ?
        GROUP BY risk_level
        """,
        (user_id, user_crop)
    )

    risk_summary = cursor.fetchall()


    # =========================================================
    # CROP-WISE RISK
    # CURRENT ASSIGNED CROP ONLY
    # =========================================================

    cursor.execute(
        """
        SELECT crop, risk_level, COUNT(*) AS count
        FROM predictions
        WHERE user_id = ?
        AND crop = ?
        GROUP BY crop, risk_level
        ORDER BY
            CASE risk_level
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END
        """,
        (user_id, user_crop)
    )

    crop_risk = cursor.fetchall()


    # =========================================================
    # DISEASE MONITORING
    # CURRENT ASSIGNED CROP ONLY
    # =========================================================

    cursor.execute(
        """
        SELECT disease_risks, COUNT(*) AS count
        FROM predictions
        WHERE user_id = ?
        AND crop = ?
        GROUP BY disease_risks
        """,
        (user_id, user_crop)
    )

    disease_summary = cursor.fetchall()


    # =========================================================
    # NOTIFICATIONS
    # =========================================================

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


    # =========================================================
    # UNREAD NOTIFICATION COUNT
    # =========================================================

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


    # =========================================================
    # HIGH-RISK ALERTS
    # CURRENT ASSIGNED CROP ONLY
    # =========================================================

    cursor.execute(
        """
        SELECT *
        FROM predictions
        WHERE user_id = ?
        AND crop = ?
        AND risk_level = 'High'
        ORDER BY id DESC
        LIMIT 10
        """,
        (user_id, user_crop)
    )

    high_risk_alerts = cursor.fetchall()


    # =========================================================
    # CROP ACTIVITIES
    # USE CURRENT ASSIGNED CROP
    # =========================================================

    latest_crop = user_crop

    crop_activities = CROP_ACTIVITIES.get(
        user_crop,
        []
    )


    # =========================================================
    # LATEST AUTOMATIC SENSOR DATA
    # CURRENT ASSIGNED CROP ONLY
    # =========================================================

    cursor.execute(
        """
        SELECT
            temperature,
            humidity,
            leaf_wetness,
            timestamp,
            crop
        FROM predictions
        WHERE user_id = ?
        AND crop = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, user_crop)
    )

    latest_sensor = cursor.fetchone()


    # =========================================================
    # LATEST IRRIGATION DATA
    # =========================================================

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

    latest_irrigation = cursor.fetchone()


    # =========================================================
    # CLOSE DATABASE
    # =========================================================

    connection.close()


    # =========================================================
    # DATASET FOR ENVIRONMENT CHARTS
    # =========================================================

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


    # =========================================================
    # MODEL INFORMATION
    # =========================================================

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


    # =========================================================
    # RENDER DASHBOARD
    # =========================================================

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

        user_name=session.get("user_name"),

        user_crop=user_crop,

        latest_crop=latest_crop,

        crop_activities=crop_activities,

        latest_sensor=latest_sensor,

        latest_irrigation=latest_irrigation

    )

@app.route("/notifications")
@login_required
def notifications():

    connection = get_db_connection()
    cursor = connection.cursor()

    user_id = session["user_id"]

    # Get all notifications
    cursor.execute(
        """
        SELECT *
        FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    )

    notification_list = cursor.fetchall()

    # Count unread notifications
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

    connection.close()

    return render_template(
        "notifications.html",
        notifications=notification_list,
        unread_count=unread_count
    )

@app.route("/notifications/read/<int:notification_id>", methods=["POST"])
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

    return redirect(url_for("notifications"))

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

        # -------------------------------------------------
        # Check email and password
        # -------------------------------------------------

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            # -------------------------------------------------
            # Check whether account is active
            # -------------------------------------------------

            if user["is_active"] == 0:

                return render_template(
                    "login.html",
                    error="❌ Your account has been deactivated by the administrator."
                )

            # -------------------------------------------------
            # Create login session
            # -------------------------------------------------

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["is_admin"] = user["is_admin"]

            # -------------------------------------------------
            # Log login activity
            # -------------------------------------------------

            log_activity(
                user["id"],
                "Logged in",
                "Farmer logged into the system"
            )

            return redirect(url_for("home"))

        # -------------------------------------------------
        # Invalid login
        # -------------------------------------------------

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

    # -----------------------------------------------------
    # GET FARMER'S ASSIGNED CROP
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT crop
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    user_crop_row = cursor.fetchone()

    if user_crop_row:
        user_crop = user_crop_row["crop"] or "Grape"
    else:
        user_crop = "Grape"

    # -----------------------------------------------------
    # GET LATEST IRRIGATION DATA
    # -----------------------------------------------------

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
        user_crop=user_crop,
        user_name=session.get("user_name")
    )

# =========================================================
# UPDATE IRRIGATION DATA + AUTOMATIC PUMP CONTROL
# =========================================================

@app.route("/update_irrigation")
@login_required
def update_irrigation():

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # GET FARMER'S ASSIGNED CROP
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT crop
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    if user:
        crop = user["crop"] or "Grape"
    else:
        crop = "Grape"

    # -----------------------------------------------------
    # SIMULATED SOIL MOISTURE SENSOR
    # -----------------------------------------------------

    import random

    soil_moisture = round(random.uniform(20, 80), 1)

    # -----------------------------------------------------
    # AUTOMATIC IRRIGATION DECISION
    # -----------------------------------------------------

    if soil_moisture < 30:

        water_status = "LOW"
        pump_status = "ON"

        message = (
            f"🚨 Soil moisture is low ({soil_moisture}%) for "
            f"{crop}. Irrigation has been started automatically."
        )

        notification_type = "Irrigation"

    elif soil_moisture <= 60:

        water_status = "MEDIUM"
        pump_status = "OFF"

        message = None
        notification_type = None

    else:

        water_status = "GOOD"
        pump_status = "OFF"

        message = None
        notification_type = None

    # -----------------------------------------------------
    # CURRENT TIME
    # -----------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # -----------------------------------------------------
    # SAVE IRRIGATION DATA
    # -----------------------------------------------------

    cursor.execute(
        """
        INSERT INTO irrigation
        (
            user_id,
            crop,
            soil_moisture,
            water_status,
            pump_status,
            auto_mode,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            crop,
            soil_moisture,
            water_status,
            pump_status,
            1,
            timestamp
        )
    )

    # -----------------------------------------------------
    # LOG IRRIGATION ACTIVITY
    # -----------------------------------------------------

    cursor.execute(
        """
        INSERT INTO activity_logs
        (
            user_id,
            activity,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            "Automatic irrigation check",
            (
                f"Crop: {crop}, "
                f"Soil Moisture: {soil_moisture}%, "
                f"Water Status: {water_status}, "
                f"Pump: {pump_status}"
            ),
            timestamp
        )
    )

    # -----------------------------------------------------
    # SMART IRRIGATION NOTIFICATION
    # -----------------------------------------------------

    if message:

        # -------------------------------------------------
        # CHECK PREVIOUS PUMP STATUS
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT pump_status
            FROM irrigation
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 2
            """,
            (user_id,)
        )

        irrigation_records = cursor.fetchall()

        previous_pump_status = None

        # First record = current
        # Second record = previous
        if len(irrigation_records) > 1:
            previous_pump_status = irrigation_records[1]["pump_status"]

        # -------------------------------------------------
        # NOTIFY ONLY WHEN PUMP CHANGES TO ON
        # -------------------------------------------------

        if previous_pump_status != "ON":

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
                VALUES (?, NULL, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    message,
                    notification_type,
                    0,
                    timestamp
                )
            )

            print(
                f"💧 Irrigation notification created "
                f"for Farmer {user_id}"
            )

        else:

            print(
                f"🔕 Duplicate irrigation notification "
                f"skipped for Farmer {user_id}"
            )

    connection.commit()
    connection.close()

    return redirect(url_for("irrigation"))

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
# AUTOMATIC SENSOR SIMULATION
# =========================================================

def generate_automatic_sensor_data(user_id, crop):
    """
    Generate simulated environmental sensor values
    and process them through the existing ML system.
    """

    import random

    # -----------------------------------------------------
    # GENERATE SENSOR VALUES
    # -----------------------------------------------------

    temperature = round(
        random.uniform(24, 32),
        1
    )

    humidity = round(
        random.uniform(60, 85),
        1
    )

    leaf_wetness = random.randint(
        0, 20
    )

    soil_moisture = round(
        random.uniform(15, 85),
        1
    )

    # -----------------------------------------------------
    # CURRENT TIME
    # -----------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # -----------------------------------------------------
    # ML PREDICTION
    # -----------------------------------------------------

    input_data = pd.DataFrame(
        [[
            temperature,
            humidity,
            leaf_wetness
        ]],
        columns=[
            "Temperature",
            "Humidity",
            "LW"
        ]
    )

    risk_level = model.predict(
        input_data
    )[0]

    # -----------------------------------------------------
    # DISEASE PREDICTION
    # -----------------------------------------------------

    disease_risks = get_disease_risks(
        crop,
        temperature,
        humidity,
        leaf_wetness
    )

    # -----------------------------------------------------
    # RECOMMENDATION
    # -----------------------------------------------------

    recommendation = get_recommendation(
        risk_level,
        crop
    )

    # -----------------------------------------------------
    # AUTOMATIC IRRIGATION
    # -----------------------------------------------------

    if soil_moisture < 30:

        water_status = "LOW"
        pump_status = "ON"

        irrigation_message = (
            f"🚨 Soil moisture is low "
            f"({soil_moisture}%) for {crop}. "
            f"Irrigation has been started automatically."
        )

    elif soil_moisture <= 60:

        water_status = "MEDIUM"
        pump_status = "OFF"

        irrigation_message = None

    else:

        water_status = "GOOD"
        pump_status = "OFF"

        irrigation_message = None

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    connection = get_db_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # CHECK PREVIOUS PUMP STATUS BEFORE SAVING NEW RECORD
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT pump_status
        FROM irrigation
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    previous_irrigation = cursor.fetchone()

    previous_pump_status = None

    if previous_irrigation:
        previous_pump_status = previous_irrigation["pump_status"]


    # -----------------------------------------------------
    # SAVE IRRIGATION DATA
    # -----------------------------------------------------

    cursor.execute(
        """
        INSERT INTO irrigation
        (
            user_id,
            crop,
            soil_moisture,
            water_status,
            pump_status,
            auto_mode,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            crop,
            soil_moisture,
            water_status,
            pump_status,
            1,
            timestamp
        )
    )

    # -----------------------------------------------------
    # SMART IRRIGATION NOTIFICATION
    # -----------------------------------------------------

    if pump_status == "ON":

        # -------------------------------------------------
        # SEND NOTIFICATION ONLY WHEN PUMP CHANGES
        # FROM OFF/NO PREVIOUS STATE TO ON
        # -------------------------------------------------

        if previous_pump_status != "ON":

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
                VALUES (?, NULL, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    irrigation_message,
                    "Irrigation",
                    0,
                    timestamp
                )
            )

            print(
                f"💧 Irrigation notification created "
                f"for Farmer {user_id}"
            )

        else:

            print(
                f"🔕 Duplicate irrigation notification "
                f"skipped for Farmer {user_id}"
            )

    # -----------------------------------------------------
    # SAVE PREDICTION
    # -----------------------------------------------------

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
            user_id
        )
    )

    prediction_id = cursor.lastrowid

    # -----------------------------------------------------
    # SMART DISEASE RISK NOTIFICATION
    # -----------------------------------------------------

    should_notify = False

    if risk_level in ["High", "Medium"]:

        # -------------------------------------------------
        # CHECK PREVIOUS PREDICTION
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT risk_level
            FROM predictions
            WHERE user_id = ?
            AND id != ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                user_id,
                prediction_id
            )
        )

        previous_prediction = cursor.fetchone()

        previous_risk = None

        if previous_prediction:
            previous_risk = previous_prediction["risk_level"]

        # -------------------------------------------------
        # DECIDE WHETHER NOTIFICATION IS NEEDED
        # -------------------------------------------------

        if previous_risk is None:
            should_notify = True

        elif previous_risk != risk_level:
            should_notify = True

        # -------------------------------------------------
        # CREATE NOTIFICATION
        # -------------------------------------------------

        if should_notify:

            if risk_level == "High":

                message = (
                    f"🚨 High disease risk detected "
                    f"for {crop}! "
                    f"Immediate preventive action is recommended."
                )

            else:

                message = (
                    f"⚠️ Medium disease risk detected "
                    f"for {crop}. "
                    f"Please monitor the crop carefully."
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
                    user_id,
                    prediction_id,
                    message,
                    risk_level,
                    0,
                    timestamp
                )
            )

            print(
                f"🔔 Notification created for Farmer "
                f"{user_id}: {risk_level} Risk"
            )

        else:

            print(
                f"🔕 Duplicate {risk_level} notification "
                f"skipped for Farmer {user_id}"
            )

    # -----------------------------------------------------
    # ACTIVITY LOG
    # -----------------------------------------------------

    cursor.execute(
        """
        INSERT INTO activity_logs
        (
            user_id,
            activity,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            "Automatic environmental monitoring",
            (
                f"Crop: {crop}, "
                f"Temperature: {temperature}°C, "
                f"Humidity: {humidity}%, "
                f"Leaf Wetness: {leaf_wetness}, "
                f"Soil Moisture: {soil_moisture}%, "
                f"Risk: {risk_level}, "
                f"Pump: {pump_status}"
            ),
            timestamp
        )
    )

    connection.commit()
    connection.close()

    # -----------------------------------------------------
    # RETURN SENSOR RESULT
    # -----------------------------------------------------

    return {
        "temperature": temperature,
        "humidity": humidity,
        "leaf_wetness": leaf_wetness,
        "soil_moisture": soil_moisture,
        "water_status": water_status,
        "pump_status": pump_status,
        "risk_level": risk_level,
        "disease_risks": disease_risks,
        "timestamp": timestamp
    }

# =========================================================
# AUTOMATIC SENSOR DATA API
# =========================================================

@app.route("/api/sensor-data", methods=["POST"])
@login_required
def sensor_data():

    data = request.get_json()

    if not data:
        return {
            "status": "error",
            "message": "No sensor data received"
        }, 400

    # -----------------------------------------------------
    # GET SENSOR DATA
    # -----------------------------------------------------

    crop = data.get("crop")
    temperature = data.get("temperature")
    humidity = data.get("humidity")
    leaf_wetness = data.get("leaf_wetness")
    soil_moisture = data.get("soil_moisture")

    # Use logged-in farmer instead of trusting user_id
    user_id = session["user_id"]

    # -----------------------------------------------------
    # VALIDATE REQUIRED DATA
    # -----------------------------------------------------

    if (
        crop is None
        or temperature is None
        or humidity is None
        or leaf_wetness is None
        or soil_moisture is None
    ):
        return {
            "status": "error",
            "message": "Missing sensor data"
        }, 400

    # -----------------------------------------------------
    # CONVERT SENSOR VALUES
    # -----------------------------------------------------

    try:

        temperature = float(temperature)
        humidity = float(humidity)
        leaf_wetness = int(leaf_wetness)
        soil_moisture = float(soil_moisture)

    except (ValueError, TypeError):

        return {
            "status": "error",
            "message": "Invalid sensor values"
        }, 400

    # -----------------------------------------------------
    # VALIDATE SENSOR RANGES
    # -----------------------------------------------------

    if not 0 <= soil_moisture <= 100:

        return {
            "status": "error",
            "message": "Soil moisture must be between 0 and 100%"
        }, 400

    if not 0 <= humidity <= 100:

        return {
            "status": "error",
            "message": "Humidity must be between 0 and 100%"
        }, 400

    if not 0 <= leaf_wetness <= 100:

        return {
            "status": "error",
            "message": "Leaf wetness must be between 0 and 100"
        }, 400

    # -----------------------------------------------------
    # DATABASE CONNECTION
    # -----------------------------------------------------

    connection = get_db_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # GET LOGGED-IN FARMER
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT id, name, crop, is_active, is_admin
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:

        connection.close()

        return {
            "status": "error",
            "message": "User not found"
        }, 404

    # -----------------------------------------------------
    # CHECK ACCOUNT STATUS
    # -----------------------------------------------------

    if user["is_active"] == 0:

        connection.close()

        return {
            "status": "error",
            "message": "User account is inactive"
        }, 403

    # -----------------------------------------------------
    # CHECK ADMIN
    # -----------------------------------------------------

    if user["is_admin"] == 1:

        connection.close()

        return {
            "status": "error",
            "message": "Sensor data is only available for farmers"
        }, 403

    # -----------------------------------------------------
    # CHECK CROP
    # -----------------------------------------------------

    if crop not in SUPPORTED_CROPS:

        connection.close()

        return {
            "status": "error",
            "message": "Invalid crop selected"
        }, 400

    # -----------------------------------------------------
    # CURRENT TIME
    # -----------------------------------------------------

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # -----------------------------------------------------
    # ML PREDICTION
    # -----------------------------------------------------

    input_data = pd.DataFrame(
        [[
            temperature,
            humidity,
            leaf_wetness
        ]],
        columns=[
            "Temperature",
            "Humidity",
            "LW"
        ]
    )

    risk_level = model.predict(input_data)[0]

    # -----------------------------------------------------
    # DISEASE PREDICTION
    # -----------------------------------------------------

    disease_risks = get_disease_risks(
        crop,
        temperature,
        humidity,
        leaf_wetness
    )

    # -----------------------------------------------------
    # RECOMMENDATION
    # -----------------------------------------------------

    recommendation = get_recommendation(
        risk_level,
        crop
    )

    # =====================================================
    # SMART IRRIGATION DECISION
    # =====================================================

    if soil_moisture < 30:

        water_status = "LOW"
        pump_status = "ON"

        irrigation_message = (
            f"🚨 Soil moisture is low ({soil_moisture}%) for "
            f"{crop}. Irrigation has been started automatically."
        )

    elif soil_moisture <= 60:

        water_status = "MEDIUM"
        pump_status = "OFF"

        irrigation_message = None

    else:

        water_status = "GOOD"
        pump_status = "OFF"

        irrigation_message = None

    # =====================================================
    # GET PREVIOUS PUMP STATUS
    # IMPORTANT: BEFORE INSERTING CURRENT RECORD
    # =====================================================

    cursor.execute(
        """
        SELECT pump_status
        FROM irrigation
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    previous_irrigation = cursor.fetchone()

    previous_pump_status = None

    if previous_irrigation:

        previous_pump_status = previous_irrigation["pump_status"]

    # =====================================================
    # SAVE IRRIGATION DATA
    # =====================================================

    cursor.execute(
        """
        INSERT INTO irrigation
        (
            user_id,
            crop,
            soil_moisture,
            water_status,
            pump_status,
            auto_mode,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            crop,
            soil_moisture,
            water_status,
            pump_status,
            1,
            timestamp
        )
    )

    # =====================================================
    # SAVE PREDICTION
    # =====================================================

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
            user_id
        )
    )

    prediction_id = cursor.lastrowid

    # =====================================================
    # IRRIGATION NOTIFICATION
    # ONLY OFF/NO STATE → ON
    # =====================================================

    if pump_status == "ON":

        if previous_pump_status != "ON":

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
                    user_id,
                    prediction_id,
                    irrigation_message,
                    "Irrigation",
                    0,
                    timestamp
                )
            )

            print(
                f"💧 API irrigation notification created "
                f"for Farmer {user_id}"
            )

        else:

            print(
                f"🔕 Duplicate API irrigation notification "
                f"skipped for Farmer {user_id}"
            )

    # =====================================================
    # DISEASE RISK NOTIFICATION
    # ONLY WHEN RISK CHANGES
    # =====================================================

    if risk_level in ["High", "Medium"]:

        cursor.execute(
            """
            SELECT risk_level
            FROM predictions
            WHERE user_id = ?
            AND id != ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                user_id,
                prediction_id
            )
        )

        previous_prediction = cursor.fetchone()

        previous_risk = None

        if previous_prediction:

            previous_risk = previous_prediction["risk_level"]

        # -------------------------------------------------
        # NOTIFY ONLY IF RISK CHANGED
        # -------------------------------------------------

        if previous_risk is None or previous_risk != risk_level:

            if risk_level == "High":

                message = (
                    f"🚨 High disease risk detected for {crop}! "
                    f"Immediate preventive action is recommended."
                )

            else:

                message = (
                    f"⚠️ Medium disease risk detected for {crop}. "
                    f"Please monitor the crop carefully."
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
                    user_id,
                    prediction_id,
                    message,
                    risk_level,
                    0,
                    timestamp
                )
            )

            print(
                f"🔔 API notification created for Farmer "
                f"{user_id}: {risk_level} Risk"
            )

        else:

            print(
                f"🔕 Duplicate API {risk_level} notification "
                f"skipped for Farmer {user_id}"
            )

    # =====================================================
    # ACTIVITY LOG
    # =====================================================

    cursor.execute(
        """
        INSERT INTO activity_logs
        (
            user_id,
            activity,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            "Automatic sensor data received",
            (
                f"{crop} - "
                f"Temperature: {temperature}°C | "
                f"Humidity: {humidity}% | "
                f"Leaf Wetness: {leaf_wetness} | "
                f"Soil Moisture: {soil_moisture}% | "
                f"Water Status: {water_status} | "
                f"Pump: {pump_status} | "
                f"Risk: {risk_level}"
            ),
            timestamp
        )
    )

    # =====================================================
    # SAVE EVERYTHING
    # =====================================================

    connection.commit()
    connection.close()

    # =====================================================
    # RETURN RESULT
    # =====================================================

    return {
        "status": "success",
        "prediction_id": prediction_id,
        "user_id": user_id,
        "crop": crop,
        "temperature": temperature,
        "humidity": humidity,
        "leaf_wetness": leaf_wetness,
        "soil_moisture": soil_moisture,
        "water_status": water_status,
        "pump_status": pump_status,
        "auto_mode": True,
        "risk_level": risk_level,
        "disease_risks": disease_risks,
        "recommendation": recommendation
    }, 200

# =========================================================
# CROP ACTIVITY & ACTIVITY HISTORY
# =========================================================

@app.route("/activity")
@login_required
def activity():

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    # =====================================================
    # GET FARMER'S ASSIGNED CROP
    # =====================================================

    cursor.execute(
        """
        SELECT crop
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    crop = "Grape"

    if user and user["crop"]:
        crop = user["crop"]

    # =====================================================
    # GET CROP-SPECIFIC ACTIVITIES
    # =====================================================

    crop_activities = CROP_ACTIVITIES.get(crop, [])

    # =====================================================
    # CHECK CURRENT TIME
    # =====================================================

    now = datetime.now()
    current_time = now.time()

    activity_schedule = []

    for index, item in enumerate(crop_activities):

        activity_time = datetime.strptime(
            item[0],
            "%I:%M %p"
        ).time()

        # Get next activity time
        next_time = None

        if index < len(crop_activities) - 1:
            next_time = datetime.strptime(
                crop_activities[index + 1][0],
                "%I:%M %p"
            ).time()

        # =================================================
        # DETERMINE STATUS
        # =================================================

        if current_time < activity_time:

            status = "upcoming"

        elif next_time and current_time < next_time:

            status = "current"

        else:

            status = "completed"

        activity_schedule.append({
            "time": item[0],
            "activity": item[1],
            "status": status
        })

    # =====================================================
    # FIND CURRENT ACTIVITY
    # =====================================================

    current_activity = None

    for item in activity_schedule:

        if item["status"] == "current":

            current_activity = item
            break

    # =====================================================
    # GET ACTIVITY HISTORY
    # =====================================================

    cursor.execute(
        """
        SELECT *
        FROM activity_logs
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 100
        """,
        (user_id,)
    )

    activities = cursor.fetchall()

    connection.close()

    # =====================================================
    # SEND DATA TO HTML
    # =====================================================

    return render_template(
        "activity.html",
        activities=activities,
        user_name=session.get("user_name"),
        crop=crop,
        crop_activities=crop_activities,
        activity_schedule=activity_schedule,
        current_activity=current_activity,
        current_time=now.strftime("%I:%M %p")
    )

# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
@admin_required
def admin_dashboard():

    connection = get_db_connection()
    cursor = connection.cursor()

    # Total users
    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM users
    """)

    total_users = cursor.fetchone()["count"]

    # Total predictions
    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM predictions
    """)

    total_predictions = cursor.fetchone()["count"]

    # Total high-risk predictions
    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM predictions
        WHERE risk_level = 'High'
    """)

    total_high_risk = cursor.fetchone()["count"]

    # All users
    cursor.execute("""
        SELECT id, name, email, phone, is_admin, created_at
        FROM users
        ORDER BY id DESC
    """)

    users = cursor.fetchall()

    # Recent activities
    cursor.execute("""
        SELECT
            activity_logs.*,
            users.name
        FROM activity_logs
        JOIN users
        ON activity_logs.user_id = users.id
        ORDER BY activity_logs.id DESC
        LIMIT 30
    """)

    activities = cursor.fetchall()

    # Recent high-risk predictions
    cursor.execute("""
        SELECT
            predictions.*,
            users.name
        FROM predictions
        JOIN users
        ON predictions.user_id = users.id
        WHERE predictions.risk_level = 'High'
        ORDER BY predictions.id DESC
        LIMIT 20
    """)

    high_risk_predictions = cursor.fetchall()

    connection.close()

    return render_template(
        "admin.html",
        user_name=session.get("user_name"),
        total_users=total_users,
        total_predictions=total_predictions,
        total_high_risk=total_high_risk,
        users=users,
        activities=activities,
        high_risk_predictions=high_risk_predictions
    )

# =========================================================
# ADMIN USER MANAGEMENT
# =========================================================

@app.route("/admin/users")
@admin_required
def admin_users():

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, email, phone, crop, is_admin, is_active, created_at
        FROM users
        ORDER BY id DESC
    """)

    users = cursor.fetchall()

    connection.close()

    return render_template(
        "admin_users.html",
        users=users,
        supported_crops=SUPPORTED_CROPS,
        user_name=session.get("user_name")
    )

@app.route("/admin/users/crop/<int:user_id>", methods=["POST"])
@admin_required
def admin_update_crop(user_id):

    crop = request.form.get("crop")

    if crop not in SUPPORTED_CROPS:
        return "Invalid crop selected.", 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET crop = ?
        WHERE id = ?
        AND is_admin = 0
        """,
        (crop, user_id)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("admin_users"))

@app.route("/admin/users/notify/<int:user_id>", methods=["GET", "POST"])
@admin_required
def admin_send_notification(user_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    # Find the farmer
    cursor.execute(
        """
        SELECT id, name, email, is_active, is_admin
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        connection.close()
        return "User not found.", 404

    # Do not allow notification to another admin
    if user["is_admin"] == 1:
        connection.close()
        return "Notifications can only be sent to farmers.", 403

    if request.method == "POST":

        message = request.form.get("message", "").strip()

        if not message:
            connection.close()

            return render_template(
                "admin_send_notification.html",
                user=user,
                error="Please enter a notification message."
            )

        # Insert notification
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
            VALUES (?, NULL, ?, ?, ?, ?)
            """,
            (
                user["id"],
                message,
                "Admin",
                0,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        connection.commit()
        connection.close()

        # Record admin activity
        log_activity(
            session["user_id"],
            "Notification sent",
            f"Notification sent to farmer: {user['name']}"
        )

        return redirect(url_for("admin_users"))

    connection.close()

    return render_template(
        "admin_send_notification.html",
        user=user
    )

# =========================================================
# ACTIVATE / DEACTIVATE USER
# =========================================================

@app.route("/admin/users/toggle/<int:user_id>", methods=["POST"])
@admin_required
def admin_toggle_user(user_id):

    # Prevent admin from changing their own status
    if user_id == session["user_id"]:
        return "You cannot deactivate your own admin account.", 403

    connection = get_db_connection()
    cursor = connection.cursor()

    # Get current status
    cursor.execute(
        """
        SELECT name, is_active
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        connection.close()
        return "User not found.", 404

    # Toggle status
    new_status = 0 if user["is_active"] == 1 else 1

    cursor.execute(
        """
        UPDATE users
        SET is_active = ?
        WHERE id = ?
        """,
        (new_status, user_id)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("admin_users"))

# =========================================================
# ADMIN USER DETAILS
# =========================================================

@app.route("/admin/users/<int:user_id>")
@admin_required
def admin_user_details(user_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    # Get user
    cursor.execute("""
        SELECT id, name, email, phone, is_admin, created_at
        FROM users
        WHERE id = ?
    """, (user_id,))

    user = cursor.fetchone()

    if not user:
        connection.close()
        return "User not found", 404

    # Get user's predictions
    cursor.execute("""
        SELECT *
        FROM predictions
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    predictions = cursor.fetchall()

    # Prediction statistics
    cursor.execute("""
        SELECT risk_level, COUNT(*) AS count
        FROM predictions
        WHERE user_id = ?
        GROUP BY risk_level
    """, (user_id,))

    risk_summary = cursor.fetchall()

    # Get user's activities
    cursor.execute("""
        SELECT *
        FROM activity_logs
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 50
    """, (user_id,))

    activities = cursor.fetchall()

    connection.close()

    return render_template(
        "admin_user_details.html",
        user=user,
        predictions=predictions,
        risk_summary=risk_summary,
        activities=activities,
        user_name=session.get("user_name")
    )

# =========================================================
# ADMIN DELETE USER
# =========================================================

@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):

    # Prevent admin from deleting their own account
    if user_id == session["user_id"]:
        return "You cannot delete your own admin account.", 403

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check whether user exists
    cursor.execute(
        "SELECT name FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        connection.close()
        return "User not found.", 404

    # Delete user's notifications
    cursor.execute(
        "DELETE FROM notifications WHERE user_id = ?",
        (user_id,)
    )

    # Delete user's activities
    cursor.execute(
        "DELETE FROM activity_logs WHERE user_id = ?",
        (user_id,)
    )

    # Delete user's predictions
    cursor.execute(
        "DELETE FROM predictions WHERE user_id = ?",
        (user_id,)
    )

    # Delete irrigation records
    cursor.execute(
        "DELETE FROM irrigation WHERE user_id = ?",
        (user_id,)
    )

    # Delete user
    cursor.execute(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("admin_users"))

# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

# =========================================================
# BACKGROUND AUTOMATIC ENVIRONMENT MONITORING
# =========================================================

def automatic_monitoring():

    print("🌱 Automatic monitoring started...")

    while True:

        try:

            connection = get_db_connection()
            cursor = connection.cursor()

            # -------------------------------------------------
            # GET ALL ACTIVE FARMERS
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id, crop
                FROM users
                WHERE is_active = 1
                AND is_admin = 0
                """
            )

            farmers = cursor.fetchall()

            connection.close()

            # -------------------------------------------------
            # PROCESS EACH FARMER
            # -------------------------------------------------

            for farmer in farmers:

                user_id = farmer["id"]
                crop = farmer["crop"]

                # If crop is empty, use Grape
                if not crop:
                    crop = "Grape"

                # Generate and process automatic sensor data
                result = generate_automatic_sensor_data(
                    user_id,
                    crop
                )

                print(
                    f"🌱 Farmer {user_id} | "
                    f"Crop: {crop} | "
                    f"Temperature: {result['temperature']}°C | "
                    f"Humidity: {result['humidity']}% | "
                    f"Soil: {result['soil_moisture']}% | "
                    f"Risk: {result['risk_level']} | "
                    f"Pump: {result['pump_status']}"
                )

        except Exception as e:

            print(
                "❌ Automatic monitoring error:",
                e
            )

        # -------------------------------------------------
        # WAIT 30 SECONDS
        # -------------------------------------------------

        time.sleep(30)

# =========================================================
# START AUTOMATIC MONITORING THREAD
# =========================================================

def start_automatic_monitoring():

    monitoring_thread = threading.Thread(
        target=automatic_monitoring,
        daemon=True
    )

    monitoring_thread.start()        


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    start_automatic_monitoring()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )