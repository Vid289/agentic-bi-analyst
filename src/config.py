"""
Central configuration. Supports multiple LLM providers (Anthropic, Google).
Switch providers by changing LLM_PROVIDER in .env — no code changes needed.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


@dataclass(frozen=True)
class Config:
    provider: str                     # "anthropic" or "google"
    anthropic_api_key: str
    google_api_key: str
    claude_model: str
    gemini_model: str
    db_path: Path
    max_agent_iterations: int

    @property
    def active_model(self) -> str:
        return self.claude_model if self.provider == "anthropic" else self.gemini_model


def _load() -> Config:
    provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
    if provider not in ("anthropic", "google"):
        raise RuntimeError(
            f"LLM_PROVIDER must be 'anthropic' or 'google', got '{provider}'."
        )

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    google_key = os.getenv("GOOGLE_API_KEY", "").strip()

    # Validate the active provider's key
    if provider == "anthropic" and (not anthropic_key or anthropic_key.startswith("sk-ant-your-key")):
        raise RuntimeError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set.")
    if provider == "google" and (not google_key or google_key.startswith("AIzaSy-your")):
        raise RuntimeError("LLM_PROVIDER=google but GOOGLE_API_KEY is not set.")

    db_path = (PROJECT_ROOT / os.getenv("DB_PATH", "data/saas.duckdb")).resolve()
    if not db_path.exists():
        raise RuntimeError(
            f"Database not found at {db_path}. Run `python database/init_db.py` first."
        )

    return Config(
        provider=provider,
        anthropic_api_key=anthropic_key,
        google_api_key=google_key,
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        db_path=db_path,
        max_agent_iterations=20,
    )


CONFIG = _load()
