# CyberAssist prototype user guide

## Access
The application runs on AWS and is accessed through an SSH tunnel.
Open http://localhost:8000 on the connected laptop.
Use synthetic inputs for demonstrations.

## Sign in
Enter your assigned username and password.
Sessions expire after one hour. Refreshing the page signs you out locally.
Use Sign out to invalidate the current session.

## Analyse an email
1. Paste a synthetic message into Email text.
2. Click Analyse email.
3. Read the classifier prediction and independent LLM assessment.
4. Inspect the evidence, suggested checks and limitations.
5. Record an approve, correct or reject decision.
6. Choose your final classification and explain your reasoning.
7. Click Save review.

## Analyse a security alert
1. Paste an alert into Synthetic alert.
2. Click Analyse alert.
3. Review the assessment and supporting evidence.
4. Record a review using suspicious, no clear threat or
   insufficient information.
5. Save the review.

## History and deletion
Click Refresh history to list your saved analyses.
Open a record to inspect its analysis and review history.
Delete removes that database record and its associated reviews.
Downloaded files, command-line results and other copies are separate.

## Interpretation
- A classifier label is a prediction, not a verified verdict.
- Agreement between models does not prove correctness.
- Matching quotations do not guarantee a correct explanation.
- Missing approval information does not establish unauthorised activity.
- Recommendations require human judgement; no response actions execute.

## Privacy
API inputs have matching email addresses replaced before model analysis.
This does not remove every identifier or establish anonymisation.
Review notes are not automatically masked.
Do not enter passwords, authentication codes or real personal data.

## Troubleshooting
- Page unavailable: check the SSH tunnel and API process.
- Sign-in failure: verify credentials; wait after repeated attempts.
- Session expired: sign in again.
- Analysis busy: another request is running; retry later.
- LLM failure: inspect the reported error; do not treat missing output
  as a safe assessment.

## Known scope
This is a development prototype, not a production security service.
