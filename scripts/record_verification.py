"""Record local nonsecret environment and verify release evidence contains no local secrets."""

import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from urllib.parse import urlsplit

from dotenv import dotenv_values

from queryguard.db import connect


def main():
    env = dotenv_values(ROOT / ".env")
    forbidden = []
    for key, value in env.items():
        if value and ("DSN" in key or "PASSWORD" in key):
            forbidden.append(value)
            if "DSN" in key and urlsplit(value).password:
                forbidden.append(urlsplit(value).password)
    paths = []
    for directory in [
        "queryguard",
        "scripts",
        "tests",
        "benchmarks",
        "artifacts",
        "docs",
        ".github",
        ".streamlit",
        "sql",
    ]:
        paths.extend(
            p
            for p in (ROOT / directory).rglob("*")
            if p.is_file() and p.suffix not in [".png", ".pyc"] and "__pycache__" not in p.parts
        )
    paths.extend(
        p for p in ROOT.iterdir() if p.is_file() and p.name != ".env" and not p.name.startswith(".env.")
    )
    leaked = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(secret in text for secret in forbidden):
            leaked.append(str(path.relative_to(ROOT)))
    if leaked:
        raise RuntimeError("Local secret detected in publishable files: " + ", ".join(leaked))
    junit = ET.parse(ROOT / "artifacts/pytest.xml").getroot()
    suite = junit.find("testsuite")
    if suite is None:
        raise RuntimeError("Missing executed pytest suite")
    # JUnit's host label is not relevant release evidence. Remove host identity,
    # preserving every actual test outcome/timing rather than publishing it.
    suite.attrib.pop("hostname", None)
    ET.ElementTree(junit).write(ROOT / "artifacts/pytest.xml", encoding="utf-8", xml_declaration=True)
    report = json.loads((ROOT / "artifacts/evaluation.json").read_text())
    with connect() as conn:
        database = {
            "server_version": conn.execute("SHOW server_version").fetchone()[0],
            "listen_addresses": conn.execute("SHOW listen_addresses").fetchone()[0],
            "port": conn.execute("SHOW port").fetchone()[0],
            "default_transaction_read_only": conn.execute("SHOW default_transaction_read_only").fetchone()[0],
            "statement_timeout": conn.execute("SHOW statement_timeout").fetchone()[0],
        }
    docker = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    compose_env = dict(
        __import__("os").environ,
        QG_ADMIN_PASSWORD="synthetic_config_check_only",
        QG_READER_PASSWORD="synthetic_reader_config_only",
    )
    compose = subprocess.run(
        ["docker", "compose", "--env-file", ".env.example", "config", "--quiet"],
        cwd=ROOT,
        env=compose_env,
        capture_output=True,
        timeout=20,
        check=False,
    )
    images = subprocess.run(
        ["docker", "image", "inspect", "postgres:16.11", "python:3.10-slim"],
        capture_output=True,
        timeout=20,
        check=False,
    )
    evidence = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.system(),
        "python": platform.python_version(),
        "database": database,
        "pytest": dict(suite.attrib),
        "evaluation_summaries": [{"mode": r["mode"], **r["summary"]} for r in report["runs"]],
        "adversarial_summary": report["adversarial_summary"],
        "secret_scan": {"publishable_text_files_scanned": len(paths), "local_secret_matches": 0},
        "docker": {
            "daemon_reachable": docker.returncode == 0,
            "server_version": docker.stdout.strip() if docker.returncode == 0 else None,
            "compose_config_validated": compose.returncode == 0,
            "containers_built_or_run": False,
            "base_images_cached": images.returncode == 0,
        },
        "live_ollama_executed": False,
        "static_typecheck_executed": False,
    }
    (ROOT / "artifacts/verification.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(
        "Release evidence verified:",
        suite.attrib["tests"],
        "tests;",
        len(paths),
        "publishable text paths checked; no local secret matches.",
    )


if __name__ == "__main__":
    main()
