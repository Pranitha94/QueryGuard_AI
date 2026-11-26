import os
from pathlib import Path

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    "customers": {
        "customer_id": "INT",
        "customer_label": "TEXT",
        "region": "TEXT",
        "segment": "TEXT",
        "signup_date": "DATE",
    },
    "products": {"product_id": "INT", "product_label": "TEXT", "category": "TEXT", "price": "DECIMAL"},
    "orders": {"order_id": "INT", "customer_id": "INT", "order_date": "DATE", "status": "TEXT"},
    "order_items": {"order_id": "INT", "product_id": "INT", "quantity": "INT", "unit_price": "DECIMAL"},
}


def connect():
    dsn = os.environ.get("QG_DATABASE_DSN") or dotenv_values(ROOT / ".env").get("QG_DATABASE_DSN")
    if not dsn:
        raise RuntimeError("Runtime database configuration missing")
    return psycopg.connect(dsn, connect_timeout=5)


def verify_runtime(connection=None):
    """Fail closed on powerful roles, memberships, schema/database creation or data writes."""
    from contextlib import nullcontext

    with nullcontext(connection) if connection is not None else connect() as conn:
        role = conn.execute(
            "SELECT rolsuper,rolcreaterole,rolcreatedb,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user"
        ).fetchone()
        if any(role):
            raise RuntimeError("Runtime role is privileged")
        if conn.execute(
            "SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user) LIMIT 1"
        ).fetchone():
            raise RuntimeError("Runtime role has memberships")
        if conn.execute(
            "SELECT has_database_privilege(current_database(),'CREATE') OR has_database_privilege(current_database(),'TEMP')"
        ).fetchone()[0]:
            raise RuntimeError("Runtime role can create database objects")
        if conn.execute(
            "SELECT 1 FROM pg_namespace WHERE has_schema_privilege(oid,'CREATE') LIMIT 1"
        ).fetchone():
            raise RuntimeError("Runtime role can create schema objects")
        if conn.execute(
            "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','v','m','p','f') AND (has_table_privilege(c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') OR has_any_column_privilege(c.oid,'INSERT,UPDATE,REFERENCES')) LIMIT 1"
        ).fetchone():
            raise RuntimeError("Runtime role has data write privileges")
        for table, columns in TABLES.items():
            for column in columns:
                if not conn.execute(
                    "SELECT has_column_privilege(%s,%s,%s)", (f"analytics.{table}", column, "SELECT")
                ).fetchone()[0]:
                    raise RuntimeError("Runtime role lacks an approved column")


def inspect_schema():
    with connect() as conn:
        rows = conn.execute(
            "SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='analytics' ORDER BY table_name,ordinal_position"
        ).fetchall()
        fks = conn.execute(
            "SELECT c.conrelid::regclass::text,c.confrelid::regclass::text,pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='analytics' AND c.contype='f' ORDER BY c.conname"
        ).fetchall()
    tables = {}
    for table, column, dtype in rows:
        if table in TABLES and column in TABLES[table]:
            tables.setdefault(table, []).append({"name": column, "type": dtype})
    return {
        "tables": tables,
        "relationships": [{"from": a, "to": b, "definition": c} for a, b, c in fks],
        "source": "live PostgreSQL metadata; no row samples",
    }
