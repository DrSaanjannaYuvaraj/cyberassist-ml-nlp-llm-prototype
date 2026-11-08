import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]

# Synthetic examples: no real emails or personal information.
# Train and test examples are explicitly separated.
training = [
    ("Verify your password immediately or your account will close.", "phishing"),
    ("You won a prize. Pay a processing fee to claim it.", "phishing"),
    ("Your mailbox is full. Submit your login credentials here.", "phishing"),
    ("Urgent payment required. Transfer money to our new bank account.", "phishing"),
    ("Security warning: reply with your password and verification code.", "phishing"),
    ("Your delivery is held. Enter your card details to release it.", "phishing"),
    ("Please find the meeting agenda for tomorrow attached.", "legitimate"),
    ("Your annual leave request has been approved.", "legitimate"),
    ("The project review is scheduled for Thursday afternoon.", "legitimate"),
    ("The monthly report is available in the usual internal portal.", "legitimate"),
    ("Please review the draft document before our team meeting.", "legitimate"),
    ("Scheduled maintenance will take place this weekend.", "legitimate"),
]

testing = [
    ("Confirm your password now to prevent account suspension.", "phishing"),
    ("Send your card number to receive your lottery reward.", "phishing"),
    ("Our team meeting has moved to Friday morning.", "legitimate"),
    ("Your requested leave dates are confirmed by your manager.", "legitimate"),
]

train_df = pd.DataFrame(training, columns=["text", "label"])
test_df = pd.DataFrame(testing, columns=["text", "label"])

train_df.to_csv(ROOT / "data/raw/train_synthetic.csv", index=False)
test_df.to_csv(ROOT / "data/raw/test_synthetic.csv", index=False)

# TF-IDF learns text features from training data only.
# Logistic regression learns the relationship between features and labels.
model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
    ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
])

model.fit(train_df["text"], train_df["label"])
predictions = model.predict(test_df["text"])

labels = ["legitimate", "phishing"]

print("\nTEST RESULTS — SMALL SYNTHETIC DATASET")
print(classification_report(
    test_df["label"],
    predictions,
    labels=labels,
    zero_division=0,
))

matrix = confusion_matrix(
    test_df["label"], predictions, labels=labels
)

print("Confusion matrix: rows = actual, columns = predicted")
print("Label order:", labels)
print(matrix)

test_df["prediction"] = predictions
test_df.to_csv(ROOT / "results/baseline_predictions.csv", index=False)

report = classification_report(
    test_df["label"],
    predictions,
    labels=labels,
    output_dict=True,
    zero_division=0,
)

with open(ROOT / "results/baseline_metrics.json", "w") as file:
    json.dump(report, file, indent=2)

joblib.dump(model, ROOT / "models/email_baseline.joblib")

print("\nSaved model: models/email_baseline.joblib")
print("Saved predictions: results/baseline_predictions.csv")
print("Saved metrics: results/baseline_metrics.json")
print("\nThis is a pipeline demonstration, not a validated phishing detector.")
