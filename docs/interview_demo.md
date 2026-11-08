# CyberAssist: five-minute demonstration

## 0:00–0:40 — Problem and design
Explain that the prototype supports initial email and alert triage.
Email classification uses TF-IDF and a trained PyTorch network.
A separate local LLM supplies an independent assessment and explanation.
FastAPI connects the models to the browser and simulated external client.

## 0:40–1:40 — Email workflow
Sign in.
Submit:
"Reply to helpdesk@example.com with your password to prevent account closure."

Show:
- Classifier prediction and LLM assessment.
- Redacted email address in the evidence.
- Suggested checks and limitations.
- Human review decision and saved record.

Assess the actual output rather than assuming the demonstration will pass.

## 1:40–2:40 — Alert workflow
Submit:
"One successful login from a new country. Device identity, VPN status,
travel information and subsequent account activity are unavailable."

Explain why missing context should remain visible.
Review the actual answer and save the appropriate human decision.

## 2:40–3:20 — Integration and security
Show API documentation without displaying credentials or session tokens.
Explain the separate integration client.
Show history and review timestamps.
Mention the verified anonymous-access and record-ownership checks.

## 3:20–4:20 — Evaluation
Present:
- PyTorch: 98.82% test accuracy against public dataset labels.
- Logistic regression: 97.94% on the same test set.
- Six synthetic alerts: 4 reference-label matches.
- Two alert responses contained unsupported claims.
- Five repeated requests: consistent assessment; median 8.702 seconds.

State dataset and sample-size limitations.

## 4:20–5:00 — Delivery and adoption
Show the project log and user guide.
Describe next steps: stakeholder requirements, realistic evaluation,
deployment hardening, actual cost measurement and staff training.
Explain that company adoption and productivity benefits are proposed,
not yet demonstrated.

## Honest scope
A personal prototype addressing realistic cybersecurity workflows.
It is not connected to Centerprise software and has not been deployed
or evaluated commercially.
