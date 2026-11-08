import time
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models/email_baseline.joblib"

# Load only the trusted model we trained ourselves.
model = joblib.load(MODEL_PATH)

print("\nCyberAssist — Email Classifier")
print("Small synthetic-data demonstration.")
print("Type an email, then press Enter.")
print("Type quit to exit.\n")

while True:
    text = input("Email: ").strip()

    if text.lower() == "quit":
        break

    if not text:
        print("Please enter some email text.\n")
        continue

    started = time.perf_counter()
    prediction = model.predict([text])[0]
    elapsed_ms = (time.perf_counter() - started) * 1000

    print(f"Prediction: {prediction}")
    print(f"Analysis time: {elapsed_ms:.2f} ms")
    print("Experimental result; human review required.\n")
