# CyberAssist

A Python prototype for AI-assisted email and security-alert analysis.

## Features
- TF-IDF with logistic regression and a PyTorch neural classifier.
- Independent explanations using Llama 3.2 3B through Ollama.
- FastAPI backend and browser dashboard.
- Argon2 password hashing and expiring in-memory sessions.
- User-owned analysis history, human reviews and deletion.
- Limited email-address masking before API model analysis.
- Simulated external-system integration client.

## Results
- Email held-out test accuracy: logistic regression 97.94%;
  PyTorch 98.82% on 2,624 records.
- Six synthetic alert examples: four reference-label matches;
  two responses contained unsupported claims.
- Email-address masking changed no classifier predictions on
  the 2,623-record validation set.

See aggregate results and documentation for limitations.

## Requirements
Python 3.12, CPU PyTorch and Ollama with llama3.2:3b.
Install CPU PyTorch using its official installation instructions,
then install the remaining dependencies from requirements.txt.

## Reproduction
Create these directories before running the scripts:
data/raw, data/processed, models, results, docs.

The synthetic baseline can be run with:
python src/train_baseline.py

For the public-data models:
1. Obtain Phishing_Email.csv from the dataset source below and save it
   as data/raw/public_emails.csv.
2. Run src/prepare_public_data.py.
3. Run src/train_public_baseline.py.
4. Run src/train_pytorch.py.

The combined analyser also reads the SYSTEM prompt from
src/explain_email.py, so retain that file.

## Application setup
1. Start Ollama and download llama3.2:3b.
2. Create an account using: python src/create_user.py
3. Start the API:
   python -m uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000
4. Access locally or through an SSH tunnel.

Account databases, trained models and public email data are not included.
Recreate them locally. Do not commit passwords, tokens or private keys.

## Dataset
Source: https://huggingface.co/datasets/zefang-liu/phishing-email-dataset

The dataset page declares LGPL-3.0. Review its terms and provenance
before reuse. The dataset itself is not redistributed here.
Source labels were not independently verified; some phishing-labelled
records resemble general spam. Near-duplicates may remain across splits.

## Limitations
This is a personal development prototype, not a production security service.
LLM outputs require human review. Masking does not establish anonymisation.
Sessions and login throttling are in-memory. Use a single API worker.
Command-line analysis scripts do not automatically apply API redaction.