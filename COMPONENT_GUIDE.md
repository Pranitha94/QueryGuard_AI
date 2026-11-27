# QueryGuard AI — beginner-friendly component guide

## The idea in one minute

Imagine an analyst asking a librarian for a report. The **interface** is the request desk. A **provider** proposes a database question in SQL. The **SQL policy** checks that proposal against a list of permitted operations. The **database role** is a second locked door. PostgreSQL calculates the answer, and the interface displays it. The provider does not get to declare its own result correct.

The default provider is **a template program, not an AI model**. It recognizes a small documented vocabulary. The optional Ollama adapter connects the same guarded path to a separately installed local model; a working adapter test is not a live-model accuracy measurement.

## 1. Python environment and dependency files

- `requirements.lock.txt` pins the installed libraries so another environment can request the same versions.
- `.venv/` is a private local Python environment, not part of the repository.
- `pyproject.toml` declares supported Python versions and configures pytest/Ruff.

A lock file reduces version drift; it does not prove that every package is vulnerability-free or installable on every operating system. Use the interpreter in the new environment for both installation and tests so packages do not land in a different Python installation.

## 2. The business database — `sql/seed.sql`

The database contains only **synthetic** business records:

|Table|Meaning|Important relationship|
|---|---|---|
|`analytics.customers`|Invented customer labels, regions, segments and signup dates|A customer can have many orders|
|`analytics.products`|Synthetic product labels, categories and prices|A product can appear in many order items|
|`analytics.orders`|Order date, customer and status|Each order refers to a customer|
|`analytics.order_items`|Quantity and recorded unit price for products in an order|Each item refers to an order and a product|

A **primary key** identifies a record. A **foreign key** points to a valid record in another table. A **join** combines related records. Item prices are recorded separately from the current product catalog price so historical revenue has a defined meaning.

This is a small deterministic demonstration dataset, not real sales data and not evidence of realistic production distributions.

## 3. Database bootstrap — `scripts/bootstrap.py`

Bootstrap prepares this project's dedicated database, seeds records and grants the runtime reader its limited permissions. Native local configuration is generated into ignored files. External/CI configuration supplies environment variables instead.

There are two different credentials:

- **Setup/admin:** creates the synthetic schema and its permissions.
- **Runtime reader:** can read only the approved data needed by analytics.

Never point a demo bootstrap script at an unrelated database. Never copy an author's `.env` into a clone, post it in an issue or send it to a model. Read the README's tested setup path and the audit's reproducibility limitations.

## 4. Database access and metadata — `queryguard/db.py`

`connect()` opens a PostgreSQL connection with a connection timeout. `verify_runtime()` checks that the role is not unexpectedly powerful and that required column permissions exist. `inspect_schema()` retrieves approved table/column information and foreign-key relationships.

**Schema metadata** describes the structure of a database, not its row contents. The provider receives no example customer rows. The code still treats metadata as untrusted context rather than instructions.

Verifying privileges repeatedly costs extra round trips, but makes the safety assumptions visible in a small local project. This is not a demonstrated high-throughput database layer.

## 5. Provider contract and prompts — `queryguard/providers.py`

A provider proposes one of three structured outcomes:

1. **query:** contains SQL to be checked;
2. **clarification:** asks the user to specify the question more clearly;
3. **refused:** declines an unavailable or unsupported request.

Pydantic checks the JSON's shape and sizes. It cannot decide whether SQL is safe; that is the policy layer's responsibility.

`TemplateProvider` maps documented question patterns to SQL. The SQL is predefined, but the **answers are calculated from the database**. `OllamaProvider` calls a locally configured model using HTTP, validates its structured output, bounds the received body and reports failures rather than secretly substituting template answers.

`retrieve_schema()` chooses tables by keywords and adds connected relationships needed for joins. On this tiny connected schema it often returns all tables. `build_prompt()` distinguishes baseline and schema-aware prompts and marks supplied data as untrusted. The template ignores prompt text, so comparing those modes does not measure prompt quality.

## 6. SQL authorization — `queryguard/policy.py`

SQLGlot converts a string into an **abstract syntax tree (AST)**: a structured representation of the query. The application then checks permitted node types, functions, tables, columns, casts, joins and complexity.

The policy resolves names through aliases, subqueries and CTEs and checks the resolved tree again. It rejects unsupported syntax rather than guessing that it is harmless. It also applies the result-row ceiling.

For example, a string starting with `SELECT` is not automatically safe: it might call an unsafe function. Conversely, a business question containing an alarming word is not itself the security decision; generated SQL still faces the AST policy and database permissions.

`ReviewedSQL` represents the policy's executable result inside the trusted Python process. It is not a cryptographic capability or an API that makes arbitrary in-process code trustworthy.

## 7. Guarded execution — `queryguard/execution.py`

Execution uses the restricted role, verifies its privileges and applies transaction-level read-only settings, timeouts and a controlled search path. It runs the reviewed SQL, fetches bounded rows and translates database failures into sanitized application errors.

- A **read-only transaction** forbids writes in that transaction.
- **Permissions** determine what a role may do, independently of that default.
- A **statement timeout** limits database execution time.
- A **lock timeout** limits waiting for database locks.
- A **row limit** bounds returned data, but does not make a large join or sort cheap.

These controls work together. None alone proves complete SQL security.

## 8. Orchestration — `queryguard/service.py`

`run_query()` connects the steps: metadata → prompt → provider → policy → database. It returns an explicit outcome and records elapsed latency. Provider, policy and execution failures remain different statuses.

Its result summary is deliberately modest: returned row and column counts. It does not invent business reasons, forecasts or causal explanations. A rich natural-language SQL explanation or narrative business insight is not implemented merely because the SQL viewer and row summary exist.

## 9. HTTP API, sessions and audit — `queryguard/api.py`

FastAPI exposes health, sessions, schema, queries, history and the saved evaluation report. Pydantic validates request bodies. Sensitive input is not echoed in validation errors.

An opaque session token keeps one session's bounded history separate from another. It is **not login or user identity**. The local API lets anyone who can reach it create a session, so its default bind address is loopback.

A semaphore limits simultaneous query operations. A lock protects process-local session and audit state. The audit stores request metadata rather than raw SQL, questions, results or credentials. Files rotate at a bounded threshold; filesystem failures return a sanitized unavailable response.

These are local-process safeguards. Multiple API workers would not share sessions or locks, and the audit is not a durable, tamper-evident compliance ledger.

## 10. Interface — `workspace.py`

Streamlit builds the browser interface in Python. It talks to the HTTP API, not directly to PostgreSQL. The four pages are presented as tabs:

- **Analytics workspace:** ask a question, inspect reviewed SQL and examine results;
- **Schema explorer:** view live approved metadata and relationships;
- **Evaluation lab:** inspect an existing executed report and its simulation warning;
- **Session history:** inspect metadata for the current backend session.

Plotly supplies charts and pandas supplies table-shaped data. The UI keeps bounded chat messages in the browser's Streamlit session. An expired API token can be renewed after a rejected request. Untrusted questions and provider messages render as plain text rather than interpreted Markdown.

## 11. Chart selection and CSV — `queryguard/presentation.py`

The presentation helpers inspect result structure to choose a simple metric, bar, line or table presentation. This is a heuristic, not statistical visualization intelligence. The user should still inspect the returned columns and values.

CSV export neutralizes formula-like text in headers and cells before a spreadsheet opens it. It does not authorize data access or guarantee the behavior of every spreadsheet program.

## 12. Evaluation — `benchmarks/`, `queryguard/evaluation.py`, `scripts/evaluate.py`

The benchmark contains reviewable questions, expected SQL or expected nonquery outcomes and ordering rules. The runtime provider is not allowed to load those answer keys.

The evaluator runs reference SQL separately against the same synthetic database and compares it with guarded execution results. It handles typed values, duplicate rows, numeric tolerance and ordered versus unordered results. Adversarial cases separately check that forbidden SQL is rejected before execution.

A report records actual per-case results and timing. Perfect template regression scores mean the documented templates matched their references, not that an LLM understands unseen business questions.

## 13. Tests and evidence — `tests/`, `scripts/smoke.py`, `artifacts/`

Pytest covers database permissions, SQL validation, provider success/failure, API sessions and UI components. Some tests require PostgreSQL; HTTP doubles deliberately simulate provider or component boundaries. Browser journeys and the smoke script exercise the running application separately.

Artifacts are **historical evidence tied to a revision and environment**, not live monitoring. Some verification commands overwrite artifacts; inspect Git status after running them. Screenshots must be captured from the actual application, not generated mockups.

## 14. Docker and GitHub Actions

`Dockerfile` and `compose.yaml` describe an application stack with separate setup and runtime responsibilities. Configuration validation is weaker evidence than building and running the full stack. See the audit for what actually ran.

The GitHub workflow creates a fresh Ubuntu environment and PostgreSQL service and executes its configured gates. A green run applies to its exact commit and job steps, not every possible installation path or model configuration.

## 15. The documentation and trust boundary

Start with `README.md`; use `AUDIT_REPORT.md`, `VERIFIED_FEATURES.md`, `TEST_RESULTS.md` and `KNOWN_LIMITATIONS.md` for current claims. `SECURITY.md` explains the threat model. `INTERVIEW_QUESTIONS.md` and `DEMO_SCRIPT.md` help present the project without overstating it.

This is a portfolio-grade **local synthetic-data demonstration**. It is not presented as a publicly deployable, authenticated, multi-tenant analytics product or a proven general-purpose AI agent.
