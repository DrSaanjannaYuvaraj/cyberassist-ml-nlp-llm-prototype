import json
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/public_v1"
RESULTS = ROOT / "results/public_baseline_v1"
RESULTS.mkdir(parents=True, exist_ok=True)

train = pd.read_csv(DATA / "train.csv", keep_default_na=False)
validation = pd.read_csv(DATA / "validation.csv", keep_default_na=False)

labels = ["legitimate", "phishing"]

# Simple reference: always predict the most common training label.
dummy = DummyClassifier(strategy="most_frequent")
dummy.fit(train[["text"]], train["label"])
dummy_predictions = dummy.predict(validation[["text"]])

dummy_report = classification_report(
    validation["label"],
    dummy_predictions,
    labels=labels,
    output_dict=True,
    zero_division=0,
)

model = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_features=50_000,
        sublinear_tf=True,
    )),
    ("classifier", LogisticRegression(
        max_iter=1000,
        random_state=42,
    )),
])

started = time.perf_counter()
model.fit(train["text"], train["label"])
training_seconds = time.perf_counter() - started

started = time.perf_counter()
predictions = model.predict(validation["text"])
batch_seconds = time.perf_counter() - started

report = classification_report(
    validation["label"],
    predictions,
    labels=labels,
    output_dict=True,
    zero_division=0,
)

matrix = confusion_matrix(
    validation["label"], predictions, labels=labels
)

print("\nVALIDATION RESULTS — PUBLIC DATA")
print(classification_report(
    validation["label"],
    predictions,
    labels=labels,
    digits=4,
    zero_division=0,
))

print("Majority-class baseline accuracy:",
      round(dummy_report["accuracy"], 4))
print("\nConfusion matrix: rows = actual, columns = predicted")
print("Label order:", labels)
print(matrix)

print(f"\nTraining time: {training_seconds:.2f} seconds")
print(f"Validation batch prediction time: {batch_seconds:.2f} seconds")
print("Timing excludes data loading and model loading.")

output = validation[
    ["text_id", "source_row", "label"]
].copy()
output["prediction"] = predictions
output.to_csv(RESULTS / "validation_predictions.csv", index=False)

metrics = {
    "evaluation_split": "validation",
    "train_rows": len(train),
    "validation_rows": len(validation),
    "classification_report": report,
    "majority_baseline_accuracy": dummy_report["accuracy"],
    "confusion_matrix_label_order": labels,
    "confusion_matrix": matrix.tolist(),
    "training_seconds": training_seconds,
    "batch_prediction_seconds": batch_seconds,
    "parameters": {
        "ngram_range": [1, 2],
        "min_df": 2,
        "max_features": 50_000,
        "sublinear_tf": True,
        "logistic_regression_C": 1.0,
        "random_seed": 42,
    },
}

with open(RESULTS / "validation_metrics.json", "w") as file:
    json.dump(metrics, file, indent=2)

model_path = ROOT / "models/email_public_baseline_v1.joblib"
joblib.dump(model, model_path)

print("\nSaved model:", model_path)
print("Saved results:", RESULTS)
print("Test set was not loaded or evaluated.")
