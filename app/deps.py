# app/deps.py
"""
Database dependencies (Portfolio/Dev)
-------------------------------------
This module wires a shared asyncpg pool with **insecure TLS** to avoid local
trust-store issues during demos. It disables certificate validation.

⚠️ Do NOT use this in production. Replace _build_ssl_context() with a
verified CA bundle and hostname checking when deploying for real.
"""
from __future__ import annotations

import ssl
from typing import Any, Dict, List, Optional

import asyncpg

from .settings import settings

__all__ = ["get_pool", "close_pool", "fetch_dicts", "fetch_one_dict"]

# Singleton pool
_pool: Optional[asyncpg.Pool] = None


def _build_ssl_context() -> ssl.SSLContext:
    """Dev-only TLS: no certificate validation (hostname + CA disabled)."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def get_pool() -> Optional[asyncpg.Pool]:
    """
    Create or return the shared connection pool.
    Returns None when DSN is not configured (file-mode supported).
    """
    global _pool
    if _pool is not None:
        return _pool

    dsn = settings.dsn()
    if not dsn:
        return None

    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=1,
        max_size=5,
        command_timeout=30,  # seconds
        ssl=_build_ssl_context(),  # DEV-ONLY
    )

    # Set a conservative per-connection server-side timeout (best effort)
    async with _pool.acquire() as conn:
        try:
            await conn.execute("SET statement_timeout = 15000;")  # 15s
        except Exception:
            # Some environments may not allow this; ignore silently.
            pass

    return _pool


async def close_pool() -> None:
    """Close the shared pool if it exists."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def fetch_dicts(pool: asyncpg.Pool, query: str, *args: Any) -> List[Dict[str, Any]]:
    """Run a SELECT and return rows as plain dicts."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


async def fetch_one_dict(pool: asyncpg.Pool, query: str, *args: Any) -> Optional[Dict[str, Any]]:
    """Run a SELECT and return a single row (dict) or None."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None
