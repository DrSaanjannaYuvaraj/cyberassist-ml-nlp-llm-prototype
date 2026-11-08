# Installation and testing guide

These instructions target Ubuntu 24.04 with Python 3.12.
The application can run on a suitable Linux computer or AWS EC2 instance.
AWS is not required. A Mac can access the AWS application through SSH.

Use synthetic inputs when demonstrating the application.

## 1. Download the project

```bash
git clone https://github.com/DrSaanjannaYuvaraj/cyberassist-ml-nlp-llm-prototype.git
cd cyberassist-ml-nlp-llm-prototype
```

While the repository is private, GitHub access is required.
Alternatively, download and extract its ZIP, then enter the extracted folder.

## 2. Create the Python environment

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip curl
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

The supplied requirements record the original environment.
Package availability may vary by platform.

Create the runtime directories:

```bash
mkdir -p data/raw data/processed models results docs
```

## 3. Download the public email dataset

Dataset page:
https://huggingface.co/datasets/zefang-liu/phishing-email-dataset

Review its licence and provenance before using it.
The repository does not redistribute the email dataset.

```bash
curl --fail --location --retry 3 \
  "https://huggingface.co/datasets/zefang-liu/phishing-email-dataset/resolve/main/Phishing_Email.csv" \
  --output data/raw/public_emails.csv
```

The source can change. The preparation script records a SHA-256 checksum.
Compare it with the supplied preparation summary when reproducing results.

## 4. Prepare data and train both classifiers

Run these in order:

```bash
python src/prepare_public_data.py
python src/train_public_baseline.py
python src/train_pytorch.py
```

The preparation script creates training, validation and test splits.
The baseline script fits the TF-IDF vectorizer.
The PyTorch script reuses that vectorizer and saves its selected checkpoint.

Expected model files:

- models/email_public_baseline_v1.joblib
- models/email_pytorch_v1.pt
- models/email_pytorch_vectorizer_v1.joblib

Load only model files you trust.

## 5. Install Ollama and download the LLM

```bash
curl -fsSL https://ollama.com/install.sh -o /tmp/ollama-install.sh
sh /tmp/ollama-install.sh
sudo systemctl start ollama
ollama pull llama3.2:3b
ollama list
```

Check the local service:

```bash
curl --fail http://127.0.0.1:11434/api/tags
```

Do not expose port 11434 publicly.

## 6. Create an analyst account

From the project root, with the Python environment active:

```bash
python src/create_user.py
```

Choose a username and a unique password of 15–256 characters.
Password entry is hidden. The application stores an Argon2 hash.

## 7. Start the API and dashboard — terminal A

```bash
source .venv/bin/activate
python -m uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000
```

Keep this terminal running. Use a single worker.

If running on your own Linux computer, open:

- Dashboard: http://localhost:8000
- API documentation: http://localhost:8000/docs

If running on AWS, follow the tunnel instructions below.

## 8. Access AWS from your Mac — terminal B

Run on your Mac, substituting your key path and current server DNS:

```bash
ssh -i /path/to/key.pem -N \
  -L 8000:127.0.0.1:8000 ubuntu@YOUR_SERVER_DNS
```

The terminal normally stays blank. Keep it running.

Open on your Mac:

- Dashboard: http://localhost:8000
- API documentation: http://localhost:8000/docs

No public inbound rules for ports 8000 or 11434 are needed.
SSH access must already be configured.

## 9. Test the email workflow

Sign in on the dashboard.

Enter this synthetic email:

> Reply to helpdesk@example.com with your password to prevent account closure.

Click Analyse email.

Check that the page displays:

- Classifier prediction.
- Independent LLM assessment.
- Explanation, evidence and suggested checks.
- Limitations and processing times.
- Analyst review controls.

The API replaces matching email addresses with [EMAIL_REDACTED]
before model analysis and database storage.

Read the actual output before approving it.
Save a review with a final classification and reason.

## 10. Test the alert workflow

Enter this synthetic alert:

> One successful login from a new country. Device identity, VPN status,
> travel information and subsequent account activity are unavailable.

Click Analyse alert.

The prototype reference assessment is insufficient_information.
Model outputs can differ and require review.

Save an alert review using one of:

- suspicious
- no_clear_threat
- insufficient_information

## 11. Test history and deletion

Click Refresh history and open a saved record.
Check that its original analysis and reviews appear.

To test deletion, create a disposable analysis and delete it.
Deletion removes its database record and associated reviews.
Downloaded files and other copies are separate.

## 12. Check authentication — terminal C on the server

Open another server terminal. Check health:

```bash
curl --fail http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ready"}
```

Check anonymous access:

```bash
curl -i http://127.0.0.1:8000/analyze/alert \
  -H "Content-Type: application/json" \
  -d '{"text":"A synthetic test alert."}'
```

Expected: HTTP 401.

For account isolation, create another account:

```bash
python src/create_user.py
```

Sign into that new account. Its history should exclude the first user's records.

Do not share passwords or returned session tokens.

## 13. Run evaluation scripts

Run from the project root with the Python environment active.

```bash
python src/evaluate_alerts.py
python src/benchmark_alert.py
python src/evaluate_masking.py
```

Purpose:

- evaluate_alerts.py: six synthetic alert cases and saved responses.
- benchmark_alert.py: five sequential requests for one alert.
- evaluate_masking.py: original versus masked classifier predictions
  on the validation split.

Avoid other analysis requests while collecting timings.
Manual review is required to identify unsupported claims.

The alert evaluation cases are visible development artifacts.
For a new independent evaluation, author separate cases before tuning.

### Held-out email evaluation

```bash
python src/evaluate_email_test.py
```

Run after model choices are fixed. Do not tune against the test set.

The repository includes the original aggregate test metrics.
The script refuses to overwrite existing metrics in
results/email_final_test/metrics.json.

For a separate reproduction run, change the script's OUTPUT directory
to a new directory, such as results/email_test_reproduction,
before executing it. Preserve the original results.

## 14. Run simulated external-software integration

Keep the API running. In another server terminal:

```bash
source .venv/bin/activate
python src/integration_demo.py
```

Enter your account details privately.
The client submits a synthetic alert, retrieves its stored result,
asks for a human review and signs out.

This simulates API integration; it does not connect to Centerprise software.

## 15. Stop and restart

- API: press Ctrl+C in terminal A.
- SSH tunnel: press Ctrl+C in terminal B.
- Restarting the API clears login sessions.
- Saved database records remain.
- Ctrl+Z suspends the server and may leave its port occupied.

Stop an AWS instance after use only when no other work requires it.

## Troubleshooting

### Address already in use

Find the process:

```bash
ss -ltnp 'sport = :8000'
```

Stop your previous API using Ctrl+C in its terminal.
Do not repeatedly start additional copies.

### Model file not found

Complete data preparation and both training scripts in the stated order.

### LLM connection failure

```bash
sudo systemctl status ollama --no-pager
curl --fail http://127.0.0.1:11434/api/tags
```

### Session expired

Sign in again. Refreshing the dashboard clears its in-memory token.

### API busy

Only one API analysis runs at a time. Wait and retry.

## Limitations

- Prototype, not a production security service.
- Dataset labels have not been independently verified.
- Near-duplicates may remain across data splits.
- LLM evaluation is small and synthetic.
- Masking covers selected email-address patterns only.
- Review notes and command-line scripts are not automatically masked.
- Authentication throttling and sessions are in-memory.
- Human approval is required; no defensive response actions execute.
