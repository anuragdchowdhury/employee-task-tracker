"""Security utilities – password hashing and session management."""

import os
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-insecure-key")
serializer = URLSafeTimedSerializer(SECRET_KEY)

SESSION_COOKIE = "session_token"
SESSION_MAX_AGE = 86400  # 24 hours


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_session_token(user_id: str, role: str) -> str:
    """Create a signed session token encoding user_id and role."""
    return serializer.dumps({"user_id": user_id, "role": role})


def decode_session_token(token: str) -> dict | None:
    """Decode and validate a session token. Returns None on failure."""
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data
    except (BadSignature, SignatureExpired):
        return None
