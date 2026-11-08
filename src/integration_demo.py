import getpass
import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"

def request(method, path, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)

def main():
    print("Simulated cybersecurity-system integration")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    token = None

    try:
        login = request("POST", "/auth/login", {
            "username": username,
            "password": password,
        })
        password = None
        token = login["access_token"]
        print("Login successful. Token is not displayed.")

        source_event_id = "SIM-ALERT-001"
        alert = (
            "85 failed SSH logins against admin in two minutes "
            "from 203.0.113.10. No successful login recorded. "
            "Source authorisation is unknown."
        )

        print("\nSubmitting synthetic event:", source_event_id)
        result = request(
            "POST", "/analyze/alert", {"text": alert}, token
        )
        analysis_id = result["id"]

        saved = request(
            "GET", f"/analyses/{analysis_id}", token=token
        )
        assert saved["id"] == analysis_id
        print("Saved analysis retrieved:", analysis_id)

        answer = saved["llm_answer"]
        if answer is None:
            print("LLM failed:", saved["llm_error"])
            return

        print("\nAssessment:", answer["assessment"])
        print("Explanation:", answer["explanation"])
        print("Suggested checks:")
        for check in answer["suggested_checks"]:
            print("-", check)

        print("Limitations:", answer["limitations"])
        print(
            "Unmatched evidence quotes:",
            saved["unsupported_evidence_quotes"],
        )

        decision = input(
            "\nYour decision [approve/correct/reject/skip]: "
        ).strip().lower()

        if decision == "skip":
            print("No review submitted.")
            return
        if decision not in {"approve", "correct", "reject"}:
            raise ValueError("Invalid decision. No review submitted.")

        label = input(
            "Final assessment "
            "[suspicious/no_clear_threat/insufficient_information]: "
        ).strip()

        if label not in {
            "suspicious", "no_clear_threat", "insufficient_information"
        }:
            raise ValueError("Invalid assessment. No review submitted.")

        notes = input("Reason for your decision: ").strip()
        if not notes or len(notes) > 2000:
            raise ValueError("Enter between 1 and 2,000 characters.")

        review = request(
            "POST",
            f"/analyses/{analysis_id}/alert-reviews",
            {
                "decision": decision,
                "final_label": label,
                "notes": notes,
            },
            token,
        )

        print("\nReview saved:", review["review_id"])
        print("Simulated event:", source_event_id)
        print("Linked CyberAssist analysis:", analysis_id)
        print("Integration demonstration completed.")

    except urllib.error.HTTPError as error:
        print(f"API request failed: HTTP {error.code}")
    except (OSError, ValueError, KeyError, AssertionError) as error:
        print("Demo failed:", error)
    finally:
        if token:
            try:
                request("POST", "/auth/logout", token=token)
                print("Session signed out.")
            except OSError:
                print("Server logout could not be confirmed.")

if __name__ == "__main__":
    main()
