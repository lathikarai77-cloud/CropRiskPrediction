import joblib
import pandas as pd

# Load trained model
model = joblib.load("grape_risk_model.pkl")

print("======================================")
print("     GRAPE DISEASE RISK PREDICTION")
print("======================================")

# Get user input
temperature = float(input("Enter Temperature (°C): "))
humidity = float(input("Enter Humidity (%): "))
lw = int(input("Enter Leaf Wetness (LW): "))

# Create input DataFrame
input_data = pd.DataFrame({
    "Temperature": [temperature],
    "Humidity": [humidity],
    "LW": [lw]
})

# Make prediction
prediction = model.predict(input_data)[0]

# Display result
print()
print("======================================")
print("       PREDICTION RESULT")
print("======================================")
print("Temperature :", temperature, "°C")
print("Humidity    :", humidity, "%")
print("Leaf Wetness:", lw)
print("--------------------------------------")
print("Risk Level  :", prediction.upper())
print("======================================")