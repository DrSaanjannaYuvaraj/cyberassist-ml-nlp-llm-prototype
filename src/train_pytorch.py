import copy
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
DATA = ROOT / "data/processed/public_v1"
OUTPUT = ROOT / "results/pytorch_v1"
OUTPUT.mkdir(parents=True, exist_ok=True)

torch.manual_seed(42)
torch.set_num_threads(2)
rng = np.random.default_rng(42)

train = pd.read_csv(DATA / "train.csv", keep_default_na=False)
validation = pd.read_csv(
    DATA / "validation.csv", keep_default_na=False
)

# Reuse the vectorizer fitted only on the training set.
baseline = joblib.load(
    ROOT / "models/email_public_baseline_v1.joblib"
)
vectorizer = baseline.named_steps["tfidf"]

X_train = vectorizer.transform(train["text"])
X_validation = vectorizer.transform(validation["text"])

label_map = {"legitimate": 0, "phishing": 1}
y_train = train["label"].map(label_map).to_numpy()
y_validation = validation["label"].map(label_map).to_numpy()

if pd.isna(y_train).any() or pd.isna(y_validation).any():
    raise ValueError("Unexpected labels found.")

input_size = X_train.shape[1]

model = nn.Sequential(
    nn.Linear(input_size, 64),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(64, 2),
)

optimizer = torch.optim.AdamW(
    model.parameters(), lr=0.001, weight_decay=0.01
)
loss_function = nn.CrossEntropyLoss()

BATCH_SIZE = 64
EPOCHS = 8

def evaluate():
    model.eval()
    predictions = []
    with torch.no_grad():
        for start in range(0, len(y_validation), BATCH_SIZE):
            # Convert only one batch to dense form to limit memory use.
            batch = X_validation[start:start + BATCH_SIZE]
            inputs = torch.from_numpy(
                batch.toarray().astype(np.float32)
            )
            predictions.extend(
                model(inputs).argmax(dim=1).tolist()
            )

    report = classification_report(
        y_validation,
        predictions,
        labels=[0, 1],
        target_names=["legitimate", "phishing"],
        output_dict=True,
        zero_division=0,
    )
    return predictions, report

best_f1 = -1
best_state = None
best_epoch = None
history = []

started = time.perf_counter()

for epoch in range(1, EPOCHS + 1):
    model.train()
    indices = rng.permutation(len(y_train))
    total_loss = 0.0

    for start in range(0, len(indices), BATCH_SIZE):
        batch_indices = indices[start:start + BATCH_SIZE]
        inputs = torch.from_numpy(
            X_train[batch_indices].toarray().astype(np.float32)
        )
        targets = torch.tensor(
            y_train[batch_indices], dtype=torch.long
        )

        optimizer.zero_grad()
        logits = model(inputs)
        loss = loss_function(logits, targets)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * len(batch_indices)

    _, report = evaluate()
    macro_f1 = report["macro avg"]["f1-score"]

    history.append({
        "epoch": epoch,
        "training_loss": total_loss / len(y_train),
        "validation_macro_f1": macro_f1,
    })

    if macro_f1 > best_f1:
        best_f1 = macro_f1
        best_epoch = epoch
        best_state = copy.deepcopy(model.state_dict())

    print(
        f"Epoch {epoch}/{EPOCHS} | "
        f"loss={total_loss / len(y_train):.4f} | "
        f"validation macro-F1={macro_f1:.4f}",
        flush=True,
    )

training_seconds = time.perf_counter() - started

model.load_state_dict(best_state)
predictions, report = evaluate()
matrix = confusion_matrix(
    y_validation, predictions, labels=[0, 1]
)

print(f"\nSelected epoch: {best_epoch}")
print("\nPYTORCH VALIDATION RESULTS")
print(classification_report(
    y_validation,
    predictions,
    labels=[0, 1],
    target_names=["legitimate", "phishing"],
    digits=4,
    zero_division=0,
))
print("Confusion matrix: rows = actual, columns = predicted")
print("Order: legitimate, phishing")
print(matrix)
print(f"Training plus epoch validation: {training_seconds:.2f} s")

torch.save({
    "state_dict": best_state,
    "input_size": input_size,
    "hidden_size": 64,
    "dropout": 0.2,
    "label_map": label_map,
    "selected_epoch": best_epoch,
}, ROOT / "models/email_pytorch_v1.pt")

joblib.dump(
    vectorizer, ROOT / "models/email_pytorch_vectorizer_v1.joblib"
)

output = validation[["text_id", "source_row", "label"]].copy()
output["prediction"] = [
    "legitimate" if value == 0 else "phishing"
    for value in predictions
]
output.to_csv(OUTPUT / "validation_predictions.csv", index=False)

with open(OUTPUT / "validation_metrics.json", "w") as file:
    json.dump({
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
        "selected_epoch": best_epoch,
        "training_and_validation_seconds": training_seconds,
        "history": history,
        "seed": 42,
        "batch_size": BATCH_SIZE,
        "learning_rate": 0.001,
        "weight_decay": 0.01,
        "representation": "Training-fitted baseline TF-IDF",
    }, file, indent=2)

print("\nModel and results saved. Test set remains untouched.")
