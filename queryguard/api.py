"""Loopback, single-user demo API. Session tokens isolate history, NOT user identity."""

import json
import os
import secrets
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import BoundedSemaphore, RLock
from time import monotonic
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from queryguard.db import ROOT, inspect_schema, verify_runtime
from queryguard.providers import OllamaProvider, TemplateProvider
from queryguard.request_limits import RequestBodyLimit
from queryguard.service import run_query


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    mode: Literal["baseline", "schema-aware"] = "schema-aware"


def create_app(provider=None, audit_path=None):
    if provider is None:
        kind = os.environ.get("QG_PROVIDER", "template")
        if kind not in ("template", "ollama"):
            raise RuntimeError("Unknown configured provider")
        provider = (
            TemplateProvider()
            if kind == "template"
            else OllamaProvider(model=os.environ.get("QG_OLLAMA_MODEL", "qwen2.5-coder:7b"))
        )
    audit_path = Path(audit_path) if audit_path else ROOT / ".local" / "audit.jsonl"
    lock, slots, sessions = RLock(), BoundedSemaphore(4), OrderedDict()

    @asynccontextmanager
    async def lifespan(app):
        verify_runtime()
        yield

    app = FastAPI(title="QueryGuard AI", version="1.0.0", lifespan=lifespan)
    app.add_middleware(RequestBodyLimit)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Default FastAPI validation errors echo supplied input; never do that here.
        return JSONResponse(status_code=422, content={"detail": "Invalid request shape or size."})

    def session(token):
        with lock:
            now = monotonic()
            for key in list(sessions):
                if now - sessions[key]["created"] > 3600:
                    del sessions[key]
            if not token or token not in sessions:
                raise HTTPException(401, "A current session token is required.")
            return sessions[token]

    @app.get("/health")
    def health():
        try:
            verify_runtime()
        except Exception:
            raise HTTPException(503, "Database unavailable or runtime role unsafe.") from None
        return {
            "status": "ok",
            "database": "ready",
            "provider": provider.label,
            "trust_boundary": "local single-user demo",
        }

    @app.post("/sessions", status_code=201)
    def new_session():
        token = secrets.token_urlsafe(32)
        with lock:
            while len(sessions) >= 100:
                sessions.popitem(last=False)
            sessions[token] = {"created": monotonic(), "history": deque(maxlen=50)}
        return {"token": token, "expires_in_seconds": 3600}

    @app.get("/schema")
    def schema(x_session_token: str | None = Header(default=None)):
        session(x_session_token)
        try:
            return inspect_schema()
        except Exception:
            raise HTTPException(503, "Schema unavailable.") from None

    @app.get("/history")
    def history(x_session_token: str | None = Header(default=None)):
        with lock:
            return {"items": list(session(x_session_token)["history"])}

    @app.delete("/history")
    def clear_history(x_session_token: str | None = Header(default=None)):
        with lock:
            session(x_session_token)["history"].clear()
        return {"cleared": True}

    @app.post("/query")
    def query(body: QueryRequest, x_session_token: str | None = Header(default=None)):
        owner = session(x_session_token)
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "Query capacity reached.")
        try:
            result = run_query(body.question, body.mode, provider)
            try:
                # Check the actual HTTP encoding boundary before recording accepted success.
                json.dumps(jsonable_encoder(result), allow_nan=False)
            except (TypeError, ValueError, OverflowError):
                result.update(
                    status="execution_error",
                    message="Result cannot be represented safely as JSON.",
                    columns=[],
                    rows=[],
                    row_count=0,
                    sql=None,
                )
                result.pop("summary", None)
            event = {
                "request_id": secrets.token_hex(12),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": result["status"],
                "mode": body.mode,
                "provider": provider.label,
                "latency_ms": result["latency_ms"],
                "row_count": result["row_count"],
            }
            with lock:
                try:
                    audit_path.parent.mkdir(parents=True, exist_ok=True)
                    # Bounded, data-minimal audit; no questions, SQL, tokens, values, DSNs or exception text.
                    if audit_path.exists() and audit_path.stat().st_size > 1_000_000:
                        audit_path.replace(audit_path.with_suffix(".previous.jsonl"))
                    with audit_path.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(event) + "\n")
                except OSError:
                    raise HTTPException(503, "Audit unavailable.") from None
                owner["history"].append(event)
            result["request_id"] = event["request_id"]
            return result
        finally:
            slots.release()

    @app.get("/evaluation")
    def evaluation(x_session_token: str | None = Header(default=None)):
        session(x_session_token)
        report = ROOT / "artifacts" / "evaluation.json"
        if not report.exists():
            raise HTTPException(404, "Evaluation has not been executed.")
        return json.loads(report.read_text(encoding="utf-8"))

    return app


app = create_app()
