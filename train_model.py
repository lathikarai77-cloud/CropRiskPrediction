import pandas as pd

# Load the dataset
data = pd.read_csv("dataset/Grape_Disease_Dataset.csv")

# Remove extra spaces from column names
data.columns = data.columns.str.strip()

print("Dataset loaded successfully!")

print("\nDataset Information:")
print(data.info())

print("\nMissing Values:")
print(data.isnull().sum())

print("\nBasic Statistics:")
print(data.describe())

print("\nUnique values in LW:")
print(data["LW"].unique())