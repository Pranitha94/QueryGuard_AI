"""Run honest template baseline/schema-aware evaluations and SQL attacks on local PostgreSQL."""

import hashlib
import json
import platform
import statistics
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from queryguard.db import connect, verify_runtime
from queryguard.evaluation import evaluate_cases
from queryguard.policy import PolicyError, review_sql
from queryguard.providers import TemplateProvider


def main():
    verify_runtime()
    questions_path = ROOT / "benchmarks/questions.json"
    attacks_path = ROOT / "benchmarks/adversarial.json"
    cases = json.loads(questions_path.read_text(encoding="utf-8"))
    attacks = json.loads(attacks_path.read_text(encoding="utf-8"))
    with connect() as conn:
        db_version = conn.execute("SHOW server_version").fetchone()[0]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": TemplateProvider.label,
        "live_llm_executed": False,
        "dataset": "fixed synthetic seed v1",
        "python": platform.python_version(),
        "postgresql": db_version,
        "sqlglot": version("sqlglot"),
        "fixture_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [questions_path, attacks_path, ROOT / "sql/seed.sql"]
        },
        "methodology": "Reference SQL independently executed as least-privilege reader; typed rows, 1e-6 numeric tolerance, ordered sequence or multiset comparison. No model answer-key lookup.",
        "limitations": [
            "Template vocabulary only; not LLM quality evidence.",
            "Fixed small synthetic dataset; no production security guarantee.",
            "No Docker or live Ollama execution.",
        ],
        "runs": [],
        "adversarial": [],
    }
    for mode in ["baseline", "schema-aware"]:
        records = evaluate_cases(cases, TemplateProvider(), mode)
        query_records = [r for r in records if r["expected_status"] == "accepted"]
        nonquery = [r for r in records if r["expected_status"] != "accepted"]
        summary = {
            "total": len(records),
            "passed": sum(r["passed"] for r in records),
            "skipped": 0,
            "expected_queries": len(query_records),
            "sql_valid_count": sum(r["sql_valid"] for r in query_records),
            "execution_correct": sum(r["passed"] for r in query_records),
            "nonquery_count": len(nonquery),
            "nonquery_correct": sum(r["passed"] for r in nonquery),
            "mean_latency_ms": round(statistics.mean(r["latency_ms"] for r in records), 3),
            "p95_latency_ms": sorted(r["latency_ms"] for r in records)[int(0.95 * (len(records) - 1))],
        }
        report["runs"].append({"mode": mode, "summary": summary, "records": records})
        print(mode, json.dumps(summary))
    for attack in attacks:
        try:
            review_sql(attack["sql"])
            status = "accepted"
        except PolicyError:
            status = "rejected"
        report["adversarial"].append(
            {
                **attack,
                "actual_status": status,
                "passed": status == attack["expected_status"],
                "execution": "AST policy executed; rejected SQL never sent to PostgreSQL",
            }
        )
    report["adversarial_summary"] = {
        "total": len(attacks),
        "rejected": sum(x["passed"] for x in report["adversarial"]),
        "skipped": 0,
    }
    artifact = ROOT / "artifacts"
    artifact.mkdir(exist_ok=True)
    (artifact / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Executed evaluation",
        "",
        f"Generated: {report['generated_at']}",
        "",
        report["provider"],
        "",
        report["methodology"],
        "",
        "|Mode|Passed / total|SQL valid / queries|Execution correct|Nonquery correct|Mean ms|p95 ms|",
        "|---|---|---|---|---|---|---|",
    ]
    for run in report["runs"]:
        s = run["summary"]
        lines.append(
            f"|{run['mode']}|{s['passed']}/{s['total']}|{s['sql_valid_count']}/{s['expected_queries']}|{s['execution_correct']}|{s['nonquery_correct']}/{s['nonquery_count']}|{s['mean_latency_ms']}|{s['p95_latency_ms']}|"
        )
    lines += [
        "",
        f"Adversarial policy rejections: {report['adversarial_summary']}",
        "",
        "Baseline/schema-aware results do not measure prompt improvements: the template provider ignores prompt text.",
        "",
        "No cases skipped. No live LLM or Docker run. SQL attacks rejected before execution; privilege denials are separately tested against PostgreSQL. See evaluation.json for typed per-case results and fixture hashes.",
    ]
    (artifact / "EVALUATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("adversarial", report["adversarial_summary"])
    if any(not r["passed"] for run in report["runs"] for r in run["records"]) or any(
        not r["passed"] for r in report["adversarial"]
    ):
        raise SystemExit("Evaluation failures; inspect artifacts/evaluation.json")


if __name__ == "__main__":
    main()
