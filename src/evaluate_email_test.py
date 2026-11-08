import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/email_final_test"
OUTPUT.mkdir(parents=True, exist_ok=True)

if (OUTPUT / "metrics.json").exists():
    raise SystemExit(
        "Final test results already exist. Review them rather than overwrite."
    )

test = pd.read_csv(
    ROOT / "data/processed/public_v1/test.csv",
    keep_default_na=False,
)

labels = ["legitimate", "phishing"]
metrics = {}
predictions_table = test[["text_id", "source_row", "label"]].copy()

def record(name, predictions, seconds):
    report = classification_report(
        test["label"],
        predictions,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(
        test["label"], predictions, labels=labels
    )

    metrics[name] = {
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
        "matrix_label_order": labels,
        "batch_prediction_seconds": seconds,
    }
    predictions_table[name] = predictions

    print(f"\n{name.upper()}")
    print(classification_report(
        test["label"],
        predictions,
        labels=labels,
        digits=4,
        zero_division=0,
    ))
    print("Matrix: rows actual, columns predicted")
    print("Order:", labels)
    print(matrix)
    print(f"Batch prediction: {seconds:.3f} seconds")

# Logistic regression: includes TF-IDF transformation.
baseline = joblib.load(
    ROOT / "models/email_public_baseline_v1.joblib"
)

started = time.perf_counter()
baseline_predictions = baseline.predict(test["text"])
record(
    "logistic_regression",
    baseline_predictions,
    time.perf_counter() - started,
)

# PyTorch: reload the previously selected checkpoint.
torch.set_num_threads(2)

checkpoint = torch.load(
    ROOT / "models/email_pytorch_v1.pt",
    map_location="cpu",
    weights_only=True,
)

model = nn.Sequential(
    nn.Linear(checkpoint["input_size"], checkpoint["hidden_size"]),
    nn.ReLU(),
    nn.Dropout(checkpoint["dropout"]),
    nn.Linear(checkpoint["hidden_size"], 2),
)
model.load_state_dict(checkpoint["state_dict"])
model.eval()

vectorizer = joblib.load(
    ROOT / "models/email_pytorch_vectorizer_v1.joblib"
)
label_names = {
    value: key for key, value in checkpoint["label_map"].items()
}

started = time.perf_counter()
features = vectorizer.transform(test["text"])
neural_predictions = []

with torch.no_grad():
    for start in range(0, len(test), 64):
        inputs = torch.from_numpy(
            features[start:start + 64].toarray().astype(np.float32)
        )
        neural_predictions.extend(
            label_names[value]
            for value in model(inputs).argmax(dim=1).tolist()
        )

record(
    "pytorch",
    neural_predictions,
    time.perf_counter() - started,
)

metrics["evaluation_details"] = {
    "split": "test",
    "rows": len(test),
    "retrained": False,
    "pytorch_selected_epoch": checkpoint["selected_epoch"],
    "timing": (
        "Single batch pass per model, including text transformation; "
        "excludes data and model loading. Not a latency benchmark."
    ),
    "limitations": (
        "Agreement with source labels, not independently verified truth. "
        "Normalised exact duplicates removed; related messages and "
        "near-duplicates may remain across splits."
    ),
}

predictions_table.to_csv(OUTPUT / "predictions.csv", index=False)
(OUTPUT / "metrics.json").write_text(json.dumps(metrics, indent=2))

print("\nSaved final test results:", OUTPUT)
print("Do not tune these models against this test set.")
