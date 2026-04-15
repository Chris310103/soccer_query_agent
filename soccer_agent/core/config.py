from __future__ import annotations

import os
from pathlib import Path


def load_local_env() -> None:
    """
    Minimal .env loader.
    Safe to call multiple times.
    """
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def get_gemini_api_key() -> str | None:
    """
    Return Gemini key from environment after loading local .env if present.
    """
    load_local_env()
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def has_gemini_api_key() -> bool:
    return bool(get_gemini_api_key())