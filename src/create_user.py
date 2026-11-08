import getpass
import os
import re
import sqlite3
from pathlib import Path

from pwdlib import PasswordHash

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "data/private"

# Restrict newly created files to this operating-system user.
os.umask(0o077)
PRIVATE.mkdir(parents=True, exist_ok=True)
PRIVATE.chmod(0o700)

DATABASE = PRIVATE / "cyberassist.db"
hasher = PasswordHash.recommended()

def main():
    username = input("Choose an analyst username: ").strip().lower()

    if not re.fullmatch(r"[a-z0-9_-]{3,40}", username):
        raise SystemExit(
            "Use 3–40 lowercase letters, numbers, underscores or hyphens."
        )

    password = getpass.getpass("Choose a password (minimum 15 characters): ")
    confirmation = getpass.getpass("Repeat the password: ")

    if len(password) < 15:
        raise SystemExit("Password must contain at least 15 characters.")

    if len(password) > 256:
        raise SystemExit("Password must not exceed 256 characters.")

    if password != confirmation:
        raise SystemExit("Passwords do not match. No account created.")

    password_hash = hasher.hash(password)

    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_utc TEXT NOT NULL
                    DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
        """)

        try:
            connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
        except sqlite3.IntegrityError:
            raise SystemExit(
                "Username already exists. Existing account was not changed."
            )

    DATABASE.chmod(0o600)
    print(f"Account created for: {username}")
    print("Password stored as an Argon2 hash.")

if __name__ == "__main__":
    main()
