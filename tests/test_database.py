import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_isolated_seed_and_runtime_privileges():
    script = ROOT / "scripts" / "bootstrap.py"
    assert script.exists(), "isolated database bootstrap must exist"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)
    from queryguard.db import connect, inspect_schema, verify_runtime

    verify_runtime()
    with connect() as conn:
        assert conn.execute("SELECT count(*) FROM analytics.orders").fetchone()[0] == 360
        assert conn.execute("SELECT count(*) FROM analytics.order_items").fetchone()[0] == 720
    assert len(inspect_schema()["tables"]) == 4


def test_runtime_cannot_write_or_create():
    import psycopg
    import pytest

    from queryguard.db import connect

    for statement in [
        "CREATE TABLE public.nope(id int)",
        "CREATE TEMP TABLE nope(id int)",
        "UPDATE analytics.orders SET status='cancelled'",
        "CREATE SCHEMA forbidden",
    ]:
        with connect() as conn:
            # Disable the convenience default: prove ACL denial, not just READ ONLY.
            conn.execute("SET TRANSACTION READ WRITE")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
    with connect() as conn:
        conn.execute("SET TRANSACTION READ WRITE")
        admin = conn.execute("SELECT rolname FROM pg_roles WHERE rolsuper LIMIT 1").fetchone()[0]
        from psycopg import sql

        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(admin)))
