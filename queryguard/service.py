"""Shared guarded orchestration. No evaluation answer keys or model summaries."""

from time import perf_counter

from queryguard.db import inspect_schema
from queryguard.execution import ExecutionError, execute
from queryguard.policy import PolicyError, review_sql
from queryguard.providers import ProviderError, build_prompt, retrieve_schema


def run_query(question, mode, provider):
    started = perf_counter()
    result = {
        "provider": provider.label,
        "mode": mode,
        "status": "provider_error",
        "message": "",
        "columns": [],
        "rows": [],
        "row_count": 0,
        "sql": None,
    }
    try:
        schema = retrieve_schema(question, inspect_schema())
        proposal = provider.generate(question, build_prompt(question, schema, mode))
        if proposal.status != "query":
            result.update(status=proposal.status, message=proposal.message)
        else:
            reviewed = review_sql(proposal.sql)
            result.update(execute(reviewed), status="accepted", message="AST reviewed; executed read-only.")
            n, c = result["row_count"], len(result["columns"])
            result["summary"] = (
                f"Returned {n} row{'' if n == 1 else 's'} and {c} column{'' if c == 1 else 's'}."
            )
    except PolicyError:
        result.update(status="rejected", message="SQL rejected by the allowlist policy.")
    except ProviderError:
        result.update(
            status="provider_error",
            message="Provider failed to return a valid structured response; no fallback was used.",
        )
    except ExecutionError:
        result.update(status="execution_error", message="Query could not be completed safely.")
    except Exception:
        result.update(status="execution_error", message="Analytics service unavailable.")
    result["latency_ms"] = round((perf_counter() - started) * 1000, 3)
    return result
