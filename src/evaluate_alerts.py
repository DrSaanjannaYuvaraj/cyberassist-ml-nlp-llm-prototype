import json
from pathlib import Path
from uuid import uuid4

import numpy as np
from analyze_alert import analyze_alert

ROOT = Path(__file__).resolve().parents[1]

# New synthetic examples; reference labels are not sent to the LLM.
examples = [
    {
        "id": "E1",
        "text": "One source attempted authentication against 40 user accounts within three minutes. All attempts failed. No authorised test is recorded.",
        "expected": "suspicious",
    },
    {
        "id": "E2",
        "text": "An administrator installed an approved security update during a documented maintenance window. The package signature was verified. No other anomalies were reported.",
        "expected": "no_clear_threat",
    },
    {
        "id": "E3",
        "text": "A workstation uploaded 2 GB to an external destination. Destination ownership, business purpose and normal transfer volume are unknown.",
        "expected": "insufficient_information",
    },
    {
        "id": "E4",
        "text": "Endpoint protection detected a known malicious executable by a verified signature and quarantined it. Execution status and other affected devices are unknown.",
        "expected": "suspicious",
    },
    {
        "id": "E5",
        "text": "A vulnerability scan originated from the approved scanner during its authorised window and matched the documented target list. No out-of-scope activity was observed.",
        "expected": "no_clear_threat",
    },
    {
        "id": "E6",
        "text": "A user account was added to an administrator group. The change ticket, approving manager and account purpose are unavailable.",
        "expected": "insufficient_information",
    },
]

results = []

for example in examples:
    result = analyze_alert(example["text"])
    answer = result["llm_answer"]
    predicted = answer["assessment"] if answer else None

    result["example_id"] = example["id"]
    result["expected_assessment"] = example["expected"]
    result["matches_reference"] = predicted == example["expected"]

    # Fill these after manually reading each complete response.
    result["manual_review"] = {
        "unsupported_claims": None,
        "appropriate_recommendations": None,
        "notes": "",
    }

    results.append(result)

    print(
        f"{example['id']} | expected={example['expected']} | "
        f"predicted={predicted} | {result['llm_seconds']}s",
        flush=True,
    )

times = [result["llm_seconds"] for result in results]
summary = {
    "prompt_version": "security_alert_v2",
    "examples": len(results),
    "reference_matches": sum(r["matches_reference"] for r in results),
    "failed_requests": sum(r["llm_error"] is not None for r in results),
    "responses_with_unmatched_quotes": sum(
        bool(r["unsupported_evidence_quotes"]) for r in results
    ),
    "median_seconds": float(np.median(times)),
    "p95_seconds": float(np.percentile(times, 95)),
    "limitation": (
        "Six synthetic examples with author-assigned labels. "
        "Timings cover serial local LLM requests, including any model loading. "
        "Manual explanation review is still required."
    ),
}

output = ROOT / "results" / f"alert_evaluation_{uuid4().hex}.json"
output.write_text(json.dumps({
    "summary": summary,
    "results": results,
}, indent=2))

print("\nSUMMARY")
print(json.dumps(summary, indent=2))
print("Saved:", output)
