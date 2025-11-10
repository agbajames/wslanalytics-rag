# tools/db_check.py
"""
Dev utility: verify Postgres connectivity + check if views are present.
- Uses certifi CA bundle (secure).
- Prints only safe diagnostics (no secrets).
- Optional: exits non-zero on failure for CI.

This is not required for running the app.
"""

from __future__ import annotations

import asyncio
import ssl
import sys
from typing import Iterable, Tuple

import asyncpg
import certifi

from app.settings import settings


def _ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


async def _exists(conn: asyncpg.Connection, schema: str, view: str) -> bool:
    # Check views correctly (not tables)
    sql = """
    select 1
    from information_schema.views
    where table_schema = $1 and table_name = $2
    limit 1
    """
    return bool(await conn.fetchrow(sql, schema, view))


async def _has_rows(conn: asyncpg.Connection, fq_view: str) -> bool:
    sql = f"select 1 from {fq_view} limit 1"
    try:
        return bool(await conn.fetchrow(sql))
    except Exception:
        return False


async def main() -> int:
    dsn = settings.dsn()
    print("Has DSN :", bool(dsn))
    print("Host    :", settings.dsn_host() or "—")

    if not dsn:
        print("No DSN built. Fill SUPABASE_* or SUPABASE_DB_URL in .env")
        return 1

    try:
        conn = await asyncpg.connect(dsn=dsn, ssl=_ssl_ctx())
    except asyncpg.InvalidPasswordError:
        print("Auth ❌  Invalid password. Check .env (watch quotes).")
        return 2
    except Exception as e:
        print("Connect ❌ ", type(e).__name__, str(e))
        return 3

    print("Connected ✅")
    ver = await conn.fetchval("select version()")
    print("Version :", (ver or "").split()[0])

    checks: Iterable[Tuple[str, str]] = [
        ("public", "vw_round_facts"),
        ("public", "vw_team_form_5"),
        ("public", "vw_player_leaders_90"),
        ("public", "vw_shot_profile"),
        ("public", "vw_set_piece_share"),
        ("public", "vw_gk_xgot"),
    ]

    ok = True
    for schema, view in checks:
        exists = await _exists(conn, schema, view)
        fq = f"{schema}.{view}"
        rows = await _has_rows(conn, fq) if exists else False
        print(f"{fq:32} exists={'yes' if exists else 'no '}, sample_row={'yes' if rows else 'no '}")
        ok = ok and exists

    await conn.close()
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
