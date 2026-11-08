import json
from pathlib import Path
from uuid import uuid4

import numpy as np
from analyze_alert import analyze_alert

ROOT = Path(__file__).resolve().parents[1]

alert = (
    "One successful login from a new country. Device identity, "
    "VPN status, travel information and subsequent account "
    "activity are unavailable."
)

results = []

for run in range(1, 6):
    result = analyze_alert(alert)
    result["run"] = run
    results.append(result)

    answer = result["llm_answer"]
    print(
        f"Run {run}: "
        f"{answer['assessment'] if answer else 'FAILED'} | "
        f"{result['llm_seconds']} seconds",
        flush=True,
    )

successful = [r for r in results if r["llm_error"] is None]
times = [r["llm_seconds"] for r in successful]
assessments = [r["llm_answer"]["assessment"] for r in successful]

summary = {
    "prompt_version": "security_alert_v2",
    "requests": len(results),
    "successful_requests": len(successful),
    "failed_requests": len(results) - len(successful),
    "assessment_counts": {
        value: assessments.count(value)
        for value in sorted(set(assessments))
    },
    "median_successful_seconds": (
        float(np.median(times)) if times else None
    ),
    "p95_successful_seconds": (
        float(np.percentile(times, 95)) if times else None
    ),
    "limitations": (
        "Five sequential requests for one repeated synthetic input. "
        "Includes any model loading and may benefit from prompt caching. "
        "Not an accuracy, concurrency or capacity benchmark."
    ),
}

output = ROOT / "results" / f"alert_repeatability_{uuid4().hex}.json"
output.write_text(json.dumps({
    "summary": summary,
    "results": results,
}, indent=2))

print(json.dumps(summary, indent=2))
print("Saved:", output)
