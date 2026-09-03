import pandas as pd

# Load cleaned dataset
data = pd.read_csv("dataset/cleaned_grape_data.csv")

# Calculate risk score
data["Risk_Score"] = 0

# Humidity condition
data.loc[data["Humidity"] >= 70, "Risk_Score"] += 2
data.loc[
    (data["Humidity"] >= 60) & (data["Humidity"] < 70),
    "Risk_Score"
] += 1

# Leaf Wetness condition
data.loc[data["LW"] >= 10, "Risk_Score"] += 2
data.loc[
    (data["LW"] >= 1) & (data["LW"] < 10),
    "Risk_Score"
] += 1

# Temperature condition
data.loc[
    (data["Temperature"] >= 20) & (data["Temperature"] <= 30),
    "Risk_Score"
] += 1

# Convert score into risk category
def classify_risk(score):
    if score >= 4:
        return "High"
    elif score >= 2:
        return "Medium"
    else:
        return "Low"

data["Risk_Level"] = data["Risk_Score"].apply(classify_risk)

# Display results
print("Risk analysis completed!")

print("\nRisk Level Distribution:")
print(data["Risk_Level"].value_counts())

print("\nSample Results:")
print(
    data[
        ["Temperature", "Humidity", "LW",
         "Risk_Score", "Risk_Level"]
    ].head(20)
)

# Save dataset with risk labels
data.to_csv(
    "dataset/risk_labeled_grape_data.csv",
    index=False
)

print("\nRisk-labeled dataset saved successfully!")