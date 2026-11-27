"""Isolated regression checks for source-checkout setup and launch scripts."""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_database_creation_uses_maintenance(monkeypatch):
    bootstrap = load_script("bootstrap")
    calls = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, statement):
            calls.append(str(statement))
            return self

        def fetchone(self):
            return None

    def connect(dsn, **kwargs):
        assert bootstrap.psycopg.conninfo.conninfo_to_dict(dsn)["dbname"] == "postgres"
        return Connection()

    monkeypatch.setattr(bootstrap.psycopg, "connect", connect)
    bootstrap.ensure_database("postgresql://admin:password@127.0.0.1:55435/queryguard")
    assert calls == ["SELECT 1 FROM pg_database WHERE datname='queryguard'", "CREATE DATABASE queryguard"]
    with pytest.raises(ValueError, match="queryguard"):
        bootstrap.ensure_database("postgresql://admin:password@127.0.0.1:55435/unrelated")


def test_bootstrap_reports_measured_not_hardcoded_row_counts(monkeypatch, capsys):
    bootstrap = load_script("bootstrap")
    monkeypatch.setenv("QG_ADMIN_DSN", "postgresql://qg_admin:synthetic@127.0.0.1:55435/queryguard")
    monkeypatch.setenv("QG_DATABASE_DSN", "postgresql://qg_reader:synthetic@127.0.0.1:55435/queryguard")
    monkeypatch.setenv("QG_READER_PASSWORD", "synthetic")
    monkeypatch.delenv("QG_DB_PORT", raising=False)
    monkeypatch.setattr(bootstrap, "ensure_database", lambda dsn: None)
    counts = iter([99, 88, 77, 66])

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, statement):
            self.value = (next(counts),) if "COUNT(*)" in str(statement) else (True,)
            return self

        def fetchone(self):
            return self.value

    monkeypatch.setattr(bootstrap.psycopg, "connect", lambda *args, **kwargs: Connection())
    bootstrap.bootstrap()
    assert "99 customers, 88 products, 77 orders, 66 items" in capsys.readouterr().out


def test_runtime_configuration_rejects_mismatched_server():
    bootstrap = load_script("bootstrap")
    admin = "postgresql://qg_admin:unused@127.0.0.1:55435/queryguard"
    reader = "postgresql://qg_reader:unused@127.0.0.1:55435/queryguard"
    bootstrap.validate_runtime(admin, reader, "unused", 55435)
    for bad in [
        reader.replace("55435", "55432"),
        reader.replace("queryguard", "other"),
        reader.replace("qg_reader", "qg_admin"),
    ]:
        with pytest.raises(ValueError, match="QG_DATABASE_DSN"):
            bootstrap.validate_runtime(admin, bad, "unused", 55435)


def test_native_refuses_occupied_port_before_start(tmp_path, monkeypatch):
    import socket
    from types import SimpleNamespace

    bootstrap = load_script("bootstrap")
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    monkeypatch.setattr(bootstrap, "LOCAL", tmp_path / ".local")
    data = tmp_path / ".local/pgdata"
    data.mkdir(parents=True)
    (data / "PG_VERSION").write_text("16")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        (tmp_path / ".env").write_text(
            f"QG_ADMIN_DSN=postgresql://qg_admin:unused@127.0.0.1:{port}/queryguard\n"
            f"QG_DATABASE_DSN=postgresql://qg_reader:unused@127.0.0.1:{port}/queryguard\n"
            "QG_READER_PASSWORD=unused\n"
        )
        for key in ("QG_ADMIN_DSN", "QG_DATABASE_DSN", "QG_DB_PORT"):
            monkeypatch.delenv(key, raising=False)
        commands = []

        def run(command, **kwargs):
            commands.append(command)
            return SimpleNamespace(returncode=3)

        monkeypatch.setattr(bootstrap.subprocess, "run", run)

        def unexpected_connect(*args, **kwargs):
            raise RuntimeError("unexpected database contact")

        monkeypatch.setattr(bootstrap.psycopg, "connect", unexpected_connect)
        with pytest.raises(RuntimeError, match="occupied"):
            bootstrap.bootstrap()
        assert all("start" not in command for command in commands)


def test_smoke_options_are_configurable(monkeypatch, tmp_path):
    smoke = load_script("smoke")
    monkeypatch.delenv("QG_API_URL", raising=False)
    monkeypatch.delenv("QG_UI_URL", raising=False)
    monkeypatch.setenv("QG_API_PORT", "18000")
    monkeypatch.setenv("QG_UI_PORT", "18501")
    options = smoke.parse_options(["--output", str(tmp_path / "smoke.json")])
    assert options.api_url == "http://127.0.0.1:18000"
    assert options.ui_url == "http://127.0.0.1:18501"
    assert options.output == tmp_path / "smoke.json"
    assert smoke.parse_options(["--api-url", "http://127.0.0.1:19000"]).api_url.endswith(":19000")
    monkeypatch.setenv("QG_API_PORT", "65536")
    with pytest.raises(ValueError, match="QG_API_PORT"):
        smoke.parse_options([])


def test_evaluator_supports_output_dir():
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/evaluate.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "--output-dir" in result.stdout


def test_verify_routes_evidence_to_requested_directory(tmp_path):
    (tmp_path / "scripts").mkdir()
    script = ROOT / "scripts/verify.sh"
    (tmp_path / "scripts/verify.sh").write_bytes(script.read_bytes().replace(b"\r\n", b"\n"))
    stub = tmp_path / ".venv/bin/python"
    stub.parent.mkdir(parents=True)
    stub.write_bytes(b'#!/usr/bin/env bash\nprintf "%s " "$@"; printf "\\n"\n')
    stub.chmod(0o755)
    result = subprocess.run(
        ["bash", "-c", "export QG_EVIDENCE_DIR=evidence/custom; bash scripts/verify.sh"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "--junitxml=evidence/custom/pytest.xml" in result.stdout
    assert "--output-dir evidence/custom" in result.stdout
    assert "artifacts/pytest.xml" not in result.stdout


def test_native_start_does_not_wait_on_inherited_capture_pipe(tmp_path, monkeypatch):
    import socket
    from types import SimpleNamespace

    bootstrap = load_script("bootstrap")
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    monkeypatch.setattr(bootstrap, "LOCAL", tmp_path / ".local")
    (tmp_path / ".local/pgdata").mkdir(parents=True)
    (tmp_path / ".local/pgdata/PG_VERSION").write_text("16")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / ".env").write_text(
        f"QG_ADMIN_DSN=postgresql://qg_admin:unused@127.0.0.1:{port}/queryguard\n"
        f"QG_DATABASE_DSN=postgresql://qg_reader:unused@127.0.0.1:{port}/queryguard\n"
        "QG_READER_PASSWORD=unused\n"
    )
    for key in ("QG_ADMIN_DSN", "QG_DATABASE_DSN", "QG_DB_PORT"):
        monkeypatch.delenv(key, raising=False)

    def run(command, **kwargs):
        if "start" in command:
            assert not kwargs.get("capture_output"), "server inherits a pipe and can hang the caller"
            return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=3)

    def stop_after_start(dsn):
        raise RuntimeError("stop-after-start")

    monkeypatch.setattr(bootstrap.subprocess, "run", run)
    monkeypatch.setattr(bootstrap, "ensure_database", stop_after_start)
    with pytest.raises(RuntimeError, match="stop-after-start"):
        bootstrap.bootstrap()


def test_database_port_validation(monkeypatch):
    bootstrap = load_script("bootstrap")
    monkeypatch.setenv("QG_DB_PORT", "55435")
    assert bootstrap.database_port() == 55435
    for value in ["0", "65536", "-1", "abc", "55435;bad", ""]:
        monkeypatch.setenv("QG_DB_PORT", value)
        with pytest.raises(ValueError, match="QG_DB_PORT"):
            bootstrap.database_port()


@pytest.mark.parametrize(
    "script,variable,default", [("run_api.sh", "QG_API_PORT", 8000), ("run_ui.sh", "QG_UI_PORT", 8501)]
)
def test_launch_rejects_invalid_port(script, variable, default, tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / script).write_bytes(
        (ROOT / "scripts" / script).read_bytes().replace(b"\r\n", b"\n")
    )
    stub = tmp_path / ".venv/bin/python"
    stub.parent.mkdir(parents=True)
    stub.write_bytes(b'#!/usr/bin/env bash\nprintf "%s\\n" "$@"\n')
    stub.chmod(0o755)
    env = {**os.environ, variable: "65536"}
    result = subprocess.run(
        ["bash", "-c", f"export {variable}=65536; exec bash scripts/{script}"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert f"{variable} must be an integer between 1 and 65535" in result.stderr
