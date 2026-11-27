"""Create only this project's isolated synthetic database. Never targets a default server."""

import os
import secrets
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LOCAL = ROOT / ".local"
LOCAL.mkdir(exist_ok=True)
import psycopg
from dotenv import dotenv_values
from psycopg import sql


def database_port():
    value = os.environ.get("QG_DB_PORT", "55432")
    if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 65535:
        raise ValueError("QG_DB_PORT must be an integer between 1 and 65535")
    return int(value)


def ensure_database(admin_dsn):
    config = psycopg.conninfo.conninfo_to_dict(admin_dsn)
    if config.get("dbname") != "queryguard":
        raise ValueError("QG_ADMIN_DSN must explicitly target the dedicated queryguard database")
    maintenance = psycopg.conninfo.make_conninfo(admin_dsn, dbname="postgres")
    with psycopg.connect(maintenance, autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname='queryguard'").fetchone():
            conn.execute("CREATE DATABASE queryguard")


def validate_runtime(admin_dsn, reader_dsn, reader_password, port=None):
    admin = psycopg.conninfo.conninfo_to_dict(admin_dsn)
    reader = psycopg.conninfo.conninfo_to_dict(reader_dsn or "")
    if admin.get("dbname") != "queryguard":
        raise ValueError("QG_ADMIN_DSN must explicitly target the dedicated queryguard database")
    if port is not None and int(admin.get("port", 5432)) != port:
        raise ValueError("QG_DB_PORT disagrees with QG_ADMIN_DSN; refusing to redirect an existing cluster")
    if (
        reader.get("dbname") != "queryguard"
        or reader.get("user") != "qg_reader"
        or reader.get("password") != reader_password
        or any(reader.get(key) != admin.get(key) for key in ("host", "hostaddr"))
        or int(reader.get("port", 5432)) != int(admin.get("port", 5432))
    ):
        raise ValueError(
            "QG_DATABASE_DSN must use qg_reader and QG_READER_PASSWORD on the QG_ADMIN_DSN server"
        )


def bootstrap():
    port = database_port()
    env_path = ROOT / ".env"
    if os.environ.get("QG_ADMIN_DSN"):
        admin_dsn = os.environ["QG_ADMIN_DSN"]
        reader_password = os.environ["QG_READER_PASSWORD"]
        validate_runtime(
            admin_dsn,
            os.environ.get("QG_DATABASE_DSN"),
            reader_password,
            port if "QG_DB_PORT" in os.environ else None,
        )
    else:
        if not env_path.exists():
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} occupied; refusing to touch an unknown server")
            admin_password, reader_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            env_path.write_text(
                f"QG_ADMIN_DSN=postgresql://qg_admin:{admin_password}@127.0.0.1:{port}/queryguard\nQG_DATABASE_DSN=postgresql://qg_reader:{reader_password}@127.0.0.1:{port}/queryguard\nQG_READER_PASSWORD={reader_password}\n",
                encoding="utf-8",
            )
        config = dotenv_values(env_path)
        admin_dsn, reader_password = config["QG_ADMIN_DSN"], config["QG_READER_PASSWORD"]
        admin = psycopg.conninfo.conninfo_to_dict(admin_dsn)
        port = database_port() if "QG_DB_PORT" in os.environ else int(admin.get("port", 55432))
        validate_runtime(
            admin_dsn,
            os.environ.get("QG_DATABASE_DSN") or config.get("QG_DATABASE_DSN"),
            reader_password,
            port,
        )
        if admin.get("host") != "127.0.0.1" or admin.get("user") != "qg_admin":
            raise ValueError("Native bootstrap requires the project-owned loopback qg_admin DSN")
        pg_bin = Path(os.environ.get("PG_BIN", "C:/Program Files/PostgreSQL/16/bin"))
        data = LOCAL / "pgdata"
        if not (data / "PG_VERSION").exists():
            if data.exists() and any(data.iterdir()):
                raise RuntimeError("Uninitialized nonempty pgdata; refusing to touch unknown storage")
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} occupied; refusing to touch an unknown server")
            pwfile = LOCAL / "init-password"
            from urllib.parse import urlsplit

            pwfile.write_text(urlsplit(admin_dsn).password, encoding="utf-8")
            try:
                subprocess.run(
                    [
                        str(pg_bin / "initdb.exe"),
                        "-D",
                        str(data),
                        "-U",
                        "qg_admin",
                        "--pwfile",
                        str(pwfile),
                        "--auth-host=scram-sha-256",
                        "--auth-local=scram-sha-256",
                        "--encoding=UTF8",
                        "--locale=C",
                    ],
                    check=True,
                    capture_output=True,
                )
            finally:
                pwfile.unlink(missing_ok=True)
            with (data / "postgresql.conf").open("a", encoding="utf-8") as f:
                f.write(f"\nlisten_addresses='127.0.0.1'\nport={port}\npassword_encryption='scram-sha-256'\n")
        status = subprocess.run([str(pg_bin / "pg_ctl.exe"), "-D", str(data), "status"], capture_output=True)
        if status.returncode == 0:
            pid_lines = (data / "postmaster.pid").read_text().splitlines()
            if int(pid_lines[3]) != port:
                raise RuntimeError("Running project cluster port disagrees with configured DSN")
        elif status.returncode == 3:
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(f"Port {port} occupied; refusing to touch an unknown server")
            subprocess.run(
                [
                    str(pg_bin / "pg_ctl.exe"),
                    "-D",
                    str(data),
                    "-l",
                    str(LOCAL / "postgres.log"),
                    "-w",
                    "-o",
                    f"-p {port}",
                    "start",
                ],
                check=True,
                # A long-lived Windows postgres can inherit PIPE handles from pg_ctl.
                # Redirect to DEVNULL instead; PostgreSQL writes its own -l logfile.
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
        else:
            raise RuntimeError("Cannot establish project PostgreSQL status; refusing to start another server")
    ensure_database(admin_dsn)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='qg_reader'").fetchone():
            conn.execute(
                sql.SQL(
                    "CREATE ROLE qg_reader LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
                ).format(sql.Literal(reader_password))
            )
        conn.execute("ALTER ROLE qg_reader SET search_path = analytics, pg_catalog")
        conn.execute("ALTER ROLE qg_reader SET statement_timeout = '2000ms'")
        conn.execute("ALTER ROLE qg_reader SET default_transaction_read_only = on")
        conn.execute("REVOKE ALL ON DATABASE queryguard FROM PUBLIC")
        conn.execute("GRANT CONNECT ON DATABASE queryguard TO qg_reader")
        conn.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
        conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")
        conn.execute("REVOKE ALL ON SCHEMA analytics FROM PUBLIC")
        conn.execute("GRANT USAGE ON SCHEMA analytics TO qg_reader")
        conn.execute((ROOT / "sql" / "seed.sql").read_text(encoding="utf-8"))
        columns = {
            "customers": "customer_id,customer_label,region,segment,signup_date",
            "products": "product_id,product_label,category,price",
            "orders": "order_id,customer_id,order_date,status",
            "order_items": "order_id,product_id,quantity,unit_price",
        }
        for table, cols in columns.items():
            conn.execute(
                sql.SQL("GRANT SELECT ({}) ON analytics.{} TO qg_reader").format(
                    sql.SQL(cols), sql.Identifier(table)
                )
            )
        counts = [
            conn.execute(
                sql.SQL("SELECT COUNT(*) FROM analytics.{}").format(sql.Identifier(table))
            ).fetchone()[0]
            for table in columns
        ]
    print(
        f"Synthetic database ready: {counts[0]} customers, {counts[1]} products, "
        f"{counts[2]} orders, {counts[3]} items; reader column grants only."
    )


if __name__ == "__main__":
    bootstrap()
