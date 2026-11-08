import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import classification_report
from torch import nn

from privacy import mask_email_addresses

ROOT = Path(__file__).resolve().parents[1]
torch.set_num_threads(2)

# Reuse the existing loading function.
from analyze_email import load_classifier

model, vectorizer, labels = load_classifier()

validation = pd.read_csv(
    ROOT / "data/processed/public_v1/validation.csv",
    keep_default_na=False,
)

masked = []
affected = 0
total_matches = 0

for text in validation["text"]:
    clean, metadata = mask_email_addresses(text)
    masked.append(clean)
    count = metadata["email_address_matches"]
    affected += int(count > 0)
    total_matches += count

def predict(texts):
    features = vectorizer.transform(texts)
    predictions = []

    with torch.no_grad():
        for start in range(0, len(texts), 64):
            inputs = torch.from_numpy(
                features[start:start + 64].toarray().astype(np.float32)
            )
            predictions.extend(
                labels[value]
                for value in model(inputs).argmax(dim=1).tolist()
            )
    return predictions

original_predictions = predict(validation["text"])
masked_predictions = predict(masked)

reports = {}
for name, predictions in [
    ("original", original_predictions),
    ("masked", masked_predictions),
]:
    reports[name] = classification_report(
        validation["label"],
        predictions,
        labels=["legitimate", "phishing"],
        output_dict=True,
        zero_division=0,
    )

summary = {
    "split": "validation",
    "rows": len(validation),
    "emails_with_address_matches": affected,
    "total_address_matches": total_matches,
    "changed_predictions": sum(
        before != after
        for before, after in zip(original_predictions, masked_predictions)
    ),
    "original_accuracy": reports["original"]["accuracy"],
    "masked_accuracy": reports["masked"]["accuracy"],
    "original_phishing_recall": reports["original"]["phishing"]["recall"],
    "masked_phishing_recall": reports["masked"]["phishing"]["recall"],
    "retrained": False,
    "scope": "Classifier only; does not evaluate LLM explanation quality.",
}

output = ROOT / "results" / f"masking_validation_{uuid4().hex}.json"
output.write_text(json.dumps({
    "summary": summary,
    "reports": reports,
}, indent=2))

print(json.dumps(summary, indent=2))
print("Saved:", output)
