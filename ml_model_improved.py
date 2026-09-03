import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# =========================================================
# LOAD DATASET
# =========================================================

data = pd.read_csv(
    "dataset/risk_labeled_grape_data.csv"
)

print("Dataset Shape:", data.shape)


# =========================================================
# INPUT FEATURES
# =========================================================

X = data[
    [
        "Temperature",
        "Humidity",
        "LW"
    ]
]


# =========================================================
# TARGET
# =========================================================

y = data["Risk_Level"]


# =========================================================
# TRAIN / TEST SPLIT
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(

    X,
    y,

    test_size=0.2,

    random_state=42,

    stratify=y
)


print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))


# =========================================================
# RANDOM FOREST MODEL
# =========================================================

model = RandomForestClassifier(

    n_estimators=200,

    random_state=42,

    class_weight="balanced"

)


# =========================================================
# TRAIN MODEL
# =========================================================

model.fit(
    X_train,
    y_train
)

print("\nModel training completed!")


# =========================================================
# PREDICTION
# =========================================================

y_pred = model.predict(
    X_test
)


# =========================================================
# ACCURACY
# =========================================================

accuracy = accuracy_score(
    y_test,
    y_pred
)

print("\n===================================")
print("MODEL PERFORMANCE")
print("===================================")

print(
    f"Accuracy: {accuracy * 100:.2f}%"
)


# =========================================================
# CLASSIFICATION REPORT
# =========================================================

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        y_pred
    )
)


# =========================================================
# CONFUSION MATRIX
# =========================================================

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        y_pred
    )
)


# =========================================================
# FEATURE IMPORTANCE
# =========================================================

print("\nFeature Importance:")

for feature, importance in zip(
    X.columns,
    model.feature_importances_
):

    print(
        f"{feature}: {importance:.4f}"
    )


# =========================================================
# SAVE MODEL
# =========================================================

joblib.dump(
    model,
    "environmental_risk_model.pkl"
)

print(
    "\nModel saved successfully as "
    "environmental_risk_model.pkl"
)