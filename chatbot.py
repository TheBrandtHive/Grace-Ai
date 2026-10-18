from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("MODEL", "openai/gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))

HERE = Path(__file__).parent


def build_system_prompt() -> str:
    system = (HERE / "system_prompt.txt").read_text()
    skill = (HERE / "skill.md").read_text()
    return f"{system}\n\n## Skill Reference\n\n{skill}"


def get_reply(messages: list[dict]) -> str:
    if not API_KEY:
        raise RuntimeError("API_KEY is not set. Add it to .env (OpenRouter).")

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    resp = httpx.post(
        f"{BASE_URL}/chat/completions", json=payload, headers=headers, timeout=60.0
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]