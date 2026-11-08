from privacy import mask_email_addresses
from typing import Literal
from records import initialise, save_analysis, get_analysis, save_review
import hashlib
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock

import torch
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from pwdlib import PasswordHash

from analyze_email import analyze, load_classifier

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data/private/cyberassist.db"
DASHBOARD = ROOT / "ui/index.html"

hasher = PasswordHash.recommended()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
bearer = HTTPBearer(auto_error=False)

analysis_lock = Lock()
session_lock = Lock()
sessions = {}
login_attempts = {}
SESSION_SECONDS = 3600

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

@asynccontextmanager
async def lifespan(app):
    torch.set_num_threads(2)
    initialise()
    app.state.classifier = load_classifier()
    yield

app = FastAPI(
    title="CyberAssist Prototype API",
    lifespan=lifespan,
)

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=1, max_length=256)

class EmailRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Login required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key = token_hash(credentials.credentials)
    with session_lock:
        session = sessions.get(key)
        if session is None or session["expires"] <= time.monotonic():
            sessions.pop(key, None)
            raise HTTPException(status_code=401, detail="Session expired or invalid.")
        return session["username"]

@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD)

@app.get("/health")
def health():
    return {"status": "ready"}

@app.post("/auth/login")
def login(request: LoginRequest):
    username = request.username.strip().lower()
    now = time.monotonic()

    # Prototype limit: five login attempts per username per minute.
    with session_lock:
        recent = [
            stamp for stamp in login_attempts.get(username, [])
            if now - stamp < 60
        ]
        if len(recent) >= 5:
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts. Wait one minute.",
            )
        login_attempts[username] = recent + [now]

    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    valid = hasher.verify(
        request.password,
        row[0] if row else dummy_hash,
    )

    if not valid or row is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password.",
        )

    token = secrets.token_urlsafe(32)
    with session_lock:
        # Remove expired sessions.
        for key in list(sessions):
            if sessions[key]["expires"] <= time.monotonic():
                del sessions[key]

        sessions[token_hash(token)] = {
            "username": username,
            "expires": time.monotonic() + SESSION_SECONDS,
        }

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": SESSION_SECONDS,
    }

@app.get("/auth/me")
def me(username: str = Depends(current_user)):
    return {"username": username}

@app.post("/auth/logout")
def logout(
    username: str = Depends(current_user),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    with session_lock:
        sessions.pop(token_hash(credentials.credentials), None)
    return {"status": "signed_out"}

@app.post("/analyze/email")
def analyze_email(
    request: EmailRequest,
    username: str = Depends(current_user),
):
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="Email cannot be blank.")

    if not analysis_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail="Analysis busy. Try again shortly.",
        )

    try:
        model, vectorizer, labels = app.state.classifier
        masked_text, privacy = mask_email_addresses(request.text)
        result = analyze(masked_text, model, vectorizer, labels)
        result["privacy"] = privacy
        result["analyst"] = username
        save_analysis(username, result)
        return result
    finally:
        analysis_lock.release()


class ReviewRequest(BaseModel):
    decision: Literal["approve", "correct", "reject"]
    final_label: Literal["legitimate", "phishing", "uncertain"]
    notes: str = Field(min_length=1, max_length=2000)

@app.get("/analyses/{analysis_id}")
def retrieve_analysis(
    analysis_id: str,
    username: str = Depends(current_user),
):
    result = get_analysis(username, analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return result

@app.post("/analyses/{analysis_id}/reviews")
def review_analysis(
    analysis_id: str,
    request: ReviewRequest,
    username: str = Depends(current_user),
):
    if not request.notes.strip():
        raise HTTPException(status_code=422, detail="Review notes required.")

    original = get_analysis(username, analysis_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    if original.get("input_type", "email") != "email":
        raise HTTPException(
            status_code=422,
            detail="Use the alert-review endpoint for security alerts.",
        )

    result = save_review(
        username, analysis_id, request.decision,
        request.final_label, request.notes.strip(),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return result

@app.get("/history")
def history(username: str = Depends(current_user)):
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute("""
            SELECT a.id, a.created_utc,
                   (SELECT COUNT(*) FROM reviews r
                    WHERE r.analysis_id = a.id) AS review_count
            FROM analyses a
            WHERE a.username = ?
            ORDER BY a.created_utc DESC
            LIMIT 50
        """, (username,)).fetchall()

    return [
        {"id": row[0], "created_utc": row[1], "review_count": row[2]}
        for row in rows
    ]

@app.get("/analyses/{analysis_id}/reviews")
def review_history(
    analysis_id: str,
    username: str = Depends(current_user),
):
    with sqlite3.connect(DATABASE) as connection:
        owned = connection.execute(
            "SELECT 1 FROM analyses WHERE id = ? AND username = ?",
            (analysis_id, username),
        ).fetchone()

        if owned is None:
            raise HTTPException(status_code=404, detail="Analysis not found.")

        connection.row_factory = sqlite3.Row
        rows = connection.execute("""
            SELECT id, username, decision, final_label, notes, created_utc
            FROM reviews
            WHERE analysis_id = ? AND username = ?
            ORDER BY id DESC
        """, (analysis_id, username)).fetchall()

    return [dict(row) for row in rows]

from analyze_alert import analyze_alert as run_alert_analysis

@app.post("/analyze/alert")
def analyze_security_alert(
    request: EmailRequest,
    username: str = Depends(current_user),
):
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="Alert cannot be blank.")

    if not analysis_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail="Analysis busy. Try again shortly.",
        )

    try:
        masked_text, privacy = mask_email_addresses(request.text)
        result = run_alert_analysis(masked_text)
        result["privacy"] = privacy
        result["analyst"] = username
        save_analysis(username, result)
        return result
    finally:
        analysis_lock.release()

class AlertReviewRequest(BaseModel):
    decision: Literal["approve", "correct", "reject"]
    final_label: Literal[
        "suspicious", "no_clear_threat", "insufficient_information"
    ]
    notes: str = Field(min_length=1, max_length=2000)

@app.post("/analyses/{analysis_id}/alert-reviews")
def review_security_alert(
    analysis_id: str,
    request: AlertReviewRequest,
    username: str = Depends(current_user),
):
    original = get_analysis(username, analysis_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    if original.get("input_type") != "security_alert":
        raise HTTPException(
            status_code=422,
            detail="This endpoint accepts security-alert reviews only.",
        )

    if not request.notes.strip():
        raise HTTPException(status_code=422, detail="Review notes required.")

    result = save_review(
        username, analysis_id, request.decision,
        request.final_label, request.notes.strip(),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return result

@app.delete("/analyses/{analysis_id}")
def delete_analysis(
    analysis_id: str,
    username: str = Depends(current_user),
):
    with sqlite3.connect(DATABASE) as connection:
        owned = connection.execute(
            "SELECT 1 FROM analyses WHERE id = ? AND username = ?",
            (analysis_id, username),
        ).fetchone()

        if owned is None:
            raise HTTPException(status_code=404, detail="Analysis not found.")

        connection.execute(
            "DELETE FROM reviews WHERE analysis_id = ?",
            (analysis_id,),
        )
        connection.execute(
            "DELETE FROM analyses WHERE id = ? AND username = ?",
            (analysis_id, username),
        )

    return {"status": "deleted", "analysis_id": analysis_id}
