"""Authentication helpers for WitchMovie's email sign-in flows."""
import hashlib
import os
import secrets
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Optional

from werkzeug.security import check_password_hash, generate_password_hash

import database as db


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def password_hash(password: str) -> str:
    return generate_password_hash(password)


def password_matches(password: str, stored_hash: str) -> bool:
    return check_password_hash(stored_hash, password)


def create_account(email: str, display_name: str, password: str) -> Dict[str, Any]:
    return db.create_account(normalize_email(email), display_name.strip(), password_hash(password))


def create_passwordless_account(email: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    return db.create_account(
        normalize_email(email),
        (display_name or email.split("@", 1)[0]).strip(),
        None,
    )


def get_user(email: str) -> Optional[Dict[str, Any]]:
    return db.get_user_by_email(normalize_email(email))


def issue_magic_token(user_id: int) -> Optional[str]:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if not db.create_magic_token(token_hash, user_id):
        return None
    return token


def consume_magic_token(token: str) -> Optional[Dict[str, Any]]:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return db.consume_magic_token(token_hash)


def send_magic_email(recipient: str, link: str) -> bool:
    host = os.environ.get("SMTP_HOST")
    sender = os.environ.get("SMTP_FROM")
    if not host or not sender:
        return False

    message = EmailMessage()
    message["Subject"] = "Your WitchMovie sign-in link"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Use this one-time link to sign in to WitchMovie. It expires in 15 minutes.\n\n"
        f"{link}\n\nIf you did not request this email, you can ignore it."
    )

    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    if os.environ.get("SMTP_USE_SSL", "0") == "1":
        with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
            if username:
                smtp.login(username, password or "")
            smtp.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if username:
                smtp.login(username, password or "")
            smtp.send_message(message)
    return True