import pandas as pd

# Load dataset
data = pd.read_csv("dataset/Grape_Disease_Dataset.csv")

# Remove extra spaces from column names
data.columns = data.columns.str.strip()

# Convert Date and Time into one DateTime column
data["DateTime"] = pd.to_datetime(
    data["Date"] + " " + data["Time"]
)

# Display the cleaned dataset
print("Data prepared successfully!")

print("\nColumns:")
print(data.columns.tolist())

print("\nFirst 5 rows:")
print(data.head())

print("\nData types:")
print(data.dtypes)

# Save the cleaned dataset
data.to_csv(
    "dataset/cleaned_grape_data.csv",
    index=False
)

print("\nCleaned dataset saved successfully!")