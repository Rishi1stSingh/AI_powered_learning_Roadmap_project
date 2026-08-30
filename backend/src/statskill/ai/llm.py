"""Small Groq-only JSON completion boundary."""
import httpx
from statskill.core.config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL

def groq_json(system: str, user: str, timeout: float = 20.0) -> dict:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")
    response = httpx.post(f"{GROQ_BASE_URL}/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json={"model": GROQ_MODEL, "temperature": 0.1, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=timeout)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
