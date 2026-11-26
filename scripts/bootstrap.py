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


def bootstrap():
    env_path = ROOT / ".env"
    if os.environ.get("QG_ADMIN_DSN"):
        admin_dsn = os.environ["QG_ADMIN_DSN"]
        reader_password = os.environ["QG_READER_PASSWORD"]
    else:
        if not env_path.exists():
            with socket.socket() as sock:
                if sock.connect_ex(("127.0.0.1", 55432)) == 0:
                    raise RuntimeError("Port 55432 occupied; refusing to touch an unknown server")
            admin_password, reader_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            env_path.write_text(
                f"QG_ADMIN_DSN=postgresql://qg_admin:{admin_password}@127.0.0.1:55432/queryguard\nQG_DATABASE_DSN=postgresql://qg_reader:{reader_password}@127.0.0.1:55432/queryguard\nQG_READER_PASSWORD={reader_password}\n",
                encoding="utf-8",
            )
        config = dotenv_values(env_path)
        admin_dsn, reader_password = config["QG_ADMIN_DSN"], config["QG_READER_PASSWORD"]
        pg_bin = Path(os.environ.get("PG_BIN", "C:/Program Files/PostgreSQL/16/bin"))
        data = LOCAL / "pgdata"
        if not data.exists():
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
                f.write("\nlisten_addresses='127.0.0.1'\nport=55432\npassword_encryption='scram-sha-256'\n")
        status = subprocess.run([str(pg_bin / "pg_ctl.exe"), "-D", str(data), "status"], capture_output=True)
        if status.returncode:
            subprocess.run(
                [
                    str(pg_bin / "pg_ctl.exe"),
                    "-D",
                    str(data),
                    "-l",
                    str(LOCAL / "postgres.log"),
                    "-w",
                    "start",
                ],
                check=True,
                capture_output=True,
            )
        maintenance = admin_dsn.rsplit("/", 1)[0] + "/postgres"
        with psycopg.connect(maintenance, autocommit=True) as conn:
            if not conn.execute("SELECT 1 FROM pg_database WHERE datname='queryguard'").fetchone():
                conn.execute("CREATE DATABASE queryguard")
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
    print(
        "Synthetic database ready: 48 customers, 12 products, 360 orders, 720 items; reader column grants only."
    )


if __name__ == "__main__":
    bootstrap()
