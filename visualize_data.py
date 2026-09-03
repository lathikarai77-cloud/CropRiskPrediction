import pandas as pd
import matplotlib.pyplot as plt

# Load risk-labeled dataset
data = pd.read_csv("dataset/risk_labeled_grape_data.csv")

# Count each risk level
risk_counts = data["Risk_Level"].value_counts()

print("Risk Level Counts:")
print(risk_counts)

# Create bar chart
plt.figure(figsize=(7, 5))

risk_counts.plot(kind="bar")

plt.title("Grape Disease Environmental Risk Distribution")
plt.xlabel("Risk Level")
plt.ylabel("Number of Records")
plt.xticks(rotation=0)

plt.tight_layout()
plt.show()