"""Application settings shared by backend services."""
from pathlib import Path
from dotenv import load_dotenv
import os
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

def _normalize_database_url(value: str) -> str:
    """Accept passwords containing @ when they were not URL-escaped."""
    if value.count("@") <= 1 or "://" not in value:
        return value
    prefix, rest = value.split("://", 1)
    credentials, host = rest.rsplit("@", 1)
    if ":" in credentials:
        user, password = credentials.split(":", 1)
        return f"{prefix}://{user}:{password.replace('@', '%40')}@{host}"
    return value

DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", "postgresql+psycopg://statskill_app:CHANGE_ME@localhost:5432/statskill"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
