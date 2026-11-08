import json
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import joblib
import numpy as np
import torch
from torch import nn

# Reuse the existing LLM prompt without running its interactive code.
# Parse only the literal SYSTEM assignment; do not import the script.
import ast
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def load_prompt():
    tree = ast.parse((ROOT / "src/explain_email.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "SYSTEM"
                for target in node.targets
            ):
                return ast.literal_eval(node.value)
    raise ValueError("SYSTEM prompt not found.")

SYSTEM = load_prompt() + """
Keep recommendations proportionate to the input.
Spelling quality does not establish whether an email is authentic.
For suspicious requests, verify using independently known contact details,
not contact details supplied in the email.
State that sender identity and account activity have not been verified.
"""

def load_classifier():
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
    labels = {
        value: key for key, value in checkpoint["label_map"].items()
    }
    return model, vectorizer, labels

def explain(email):
    payload = {
        "model": "llama3.2:3b",
        "system": SYSTEM,
        "prompt": json.dumps({"email_text": email}),
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 500,
        },
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        api_result = json.load(response)

    if api_result.get("done_reason") == "length":
        raise ValueError("LLM response reached its output limit.")

    answer = json.loads(api_result["response"])
    required = {
        "assessment", "explanation", "evidence",
        "suggested_checks", "limitations",
    }
    if not isinstance(answer, dict) or set(answer) != required:
        raise ValueError("Invalid LLM output fields.")

    if answer["assessment"] not in {
        "suspicious", "no_clear_threat", "insufficient_information"
    }:
        raise ValueError("Invalid LLM assessment.")

    for field in ["explanation", "limitations"]:
        if not isinstance(answer[field], str):
            raise ValueError(f"Invalid {field}.")

    for field in ["evidence", "suggested_checks"]:
        if not isinstance(answer[field], list) or not all(
            isinstance(item, str) for item in answer[field]
        ):
            raise ValueError(f"Invalid {field}.")

    unsupported = [
        quote for quote in answer["evidence"]
        if not quote.strip() or quote not in email
    ]
    return answer, unsupported

def analyze(email, model, vectorizer, labels):
    email = email.strip()
    if not email or len(email) > 4000:
        raise ValueError("Enter between 1 and 4,000 characters.")

    started = time.perf_counter()
    features = vectorizer.transform([email])
    inputs = torch.from_numpy(features.toarray().astype(np.float32))

    with torch.no_grad():
        prediction = labels[model(inputs).argmax(dim=1).item()]

    classifier_seconds = time.perf_counter() - started

    llm_started = time.perf_counter()
    answer = None
    unsupported = None
    error = None

    try:
        answer, unsupported = explain(email)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        error = str(exc)

    llm_seconds = time.perf_counter() - llm_started

    # These labels differ in meaning; this is a review signal,
    # not proof that either component is correct.
    disagreement = None
    if answer is not None:
        if answer["assessment"] == "insufficient_information":
            disagreement = "llm_uncertain"
        else:
            mapped = {
                "suspicious": "phishing",
                "no_clear_threat": "legitimate",
            }[answer["assessment"]]
            disagreement = (
                "aligned" if mapped == prediction else "review_disagreement"
            )

    return {
        "id": uuid4().hex,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "email": email,
        "classifier_model": "email_pytorch_v1",
        "classifier_prediction": prediction,
        "llm_model": "llama3.2:3b",
        "prompt_version": "email_combined_v2",
        "llm_answer": answer,
        "unsupported_evidence_quotes": unsupported,
        "llm_error": error,
        "comparison": disagreement,
        "classifier_seconds": round(classifier_seconds, 4),
        "llm_seconds": round(llm_seconds, 3),
        "total_seconds": round(time.perf_counter() - started, 3),
        "human_review_required": True,
    }

def main():
    torch.set_num_threads(2)
    model, vectorizer, labels = load_classifier()
    email = input("Enter a short synthetic email: ")
    result = analyze(email, model, vectorizer, labels)

    output = ROOT / "results" / f"combined_{result['id']}.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    print("\nSaved:", output)
    print("Timings exclude initial classifier loading.")
    print("Agreement and matching quotations do not prove correctness.")

if __name__ == "__main__":
    main()
