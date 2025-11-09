# app/settings.py
"""
Settings: load .env, expose a safe Postgres DSN, and model defaults.
- Prefers raw components (handles special chars via URL-encoding).
- Falls back to SUPABASE_DB_URL and ensures sslmode=require.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus
from pathlib import Path
from dotenv import load_dotenv

__all__ = ["settings", "Settings"]

# Load .env from repo root
ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)  # dev-friendly: .env wins locally


@dataclass(frozen=True)
class Settings:
    # Postgres / Supabase
    SUPABASE_DB_URL: Optional[str] = os.getenv("SUPABASE_DB_URL") or None
    SUPABASE_USER: Optional[str] = os.getenv("SUPABASE_USER") or None
    SUPABASE_PASSWORD: Optional[str] = os.getenv("SUPABASE_PASSWORD") or None
    SUPABASE_HOST: Optional[str] = os.getenv("SUPABASE_HOST") or None
    SUPABASE_DB: str = os.getenv("SUPABASE_DB", "postgres")
    SUPABASE_PORT: str = os.getenv("SUPABASE_PORT", "5432")

    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL: str = os.getenv("MODEL", "gpt-4o-mini")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1800"))

    def dsn(self) -> Optional[str]:
        """Build a safe DSN string or return None when not configured."""
        # Prefer components (avoids URL-encoding pitfalls)
        if self.SUPABASE_USER and self.SUPABASE_PASSWORD and self.SUPABASE_HOST:
            pw = quote_plus(self.SUPABASE_PASSWORD)
            return (
                f"postgresql://{self.SUPABASE_USER}:{pw}"
                f"@{self.SUPABASE_HOST}:{self.SUPABASE_PORT}/{self.SUPABASE_DB}"
                f"?sslmode=require"
            )
        # Fallback DSN (ensure sslmode=require)
        if self.SUPABASE_DB_URL:
            dsn = self.SUPABASE_DB_URL
            if "sslmode=" not in dsn:
                dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
            return dsn
        return None

    # Convenience
    def has_db(self) -> bool:
        return self.dsn() is not None

    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    def dsn_host(self) -> str:
        d = self.dsn() or ""
        try:
            after_at = d.split("@", 1)[1]
            host = after_at.split("/", 1)[0]
            return host.split(":", 1)[0]
        except Exception:
            return ""


settings = Settings()
