# Interview guide

## 60-second explanation

QueryGuard AI is a synthetic PostgreSQL analytics workspace. The interesting engineering is not pretending a model always writes correct SQL: it is separating an untrusted structured proposal from authorization and execution. FastAPI retrieves approved schema metadata, obtains a proposal, performs fail-closed SQLGlot AST and lineage checks, then executes serialized reviewed SQL using a least-privilege role inside a bounded read-only transaction. Streamlit exposes the SQL, status, factual result shape, charts and evidence. The default provider is honestly simulated templates; optional Ollama is contract-tested, not live-benchmarked.

## Demonstration sequence

1. Run the dedicated database and `bash scripts/run_api.sh`, then `bash scripts/run_ui.sh`.
2. Show revenue by category: explain the join through orders/order_items and the completed-status filter.
3. Show monthly revenue for 2024: explain date boundaries, grouping and time-series chart selection.
4. Show average order value for completed orders: aggregate item totals per order before averaging.
5. Show revenue: ambiguity is a first-class clarification, not hallucinated business scope.
6. Read the admin password: refusal. Distinguish a template refusal from the **separate** SQL policy rejecting a malicious model proposal.
7. Open Evaluation lab and then the actual per-record JSON, not just a headline percentage.
8. Explain privilege tests that disable default read-only mode before proving ACL denials.

## Questions to be ready for

**Why not regex-based SQL safety?** Nested statements, CTEs, schema qualification, function calls and aliases defeat keyword screening. Parse ASTs, enforce explicit allowed constructs, resolve lineage, recheck the qualified tree and execute only its serialization. Regex in the demo provider chooses vocabulary; it is not the security boundary.

**Is SQLGlot qualification sufficient?** No. It resolves names but can resolve unauthorized names. The policy separately restricts physical tables/columns/functions/types and traverses nested scopes before and after qualification.

**Why a real read-only role if SQL is validated?** An independent DB privilege boundary catches application mistakes. `default_transaction_read_only` is a convenience setting a role can change; actual ACL grants must prevent writes, CREATE/TEMP and role escalation. Tests explicitly switch READ WRITE and observe `InsufficientPrivilege`.

**How do you cap results without changing aggregate meaning?** Limit the outer query to at most 200 rows, preserving smaller literal limits, and bound fetching. Do not pre-limit inputs before aggregation. Execution still has a SQL timeout because a one-row aggregate can be expensive.

**What does the benchmark measure?** 105 distinct reviewable questions, 78 expected queries, 12 clarifications and 15 refusals. References are independently authored SQL executed through a separate trusted fixture path against the same seed. Compare typed results, multiplicity, nulls and ordering, with 1e-6 numeric tolerance. Wrong-reference regression confirms the evaluator detects a 361-vs-360 disagreement. Both template settings passed 105/105; this is coverage of the documented template vocabulary, not general NL-to-SQL accuracy.

**Does schema-aware prompting improve accuracy?** Not demonstrated. The template provider ignores prompt text, so its two settings are equivalent by design. A real comparison requires a configured live model, held-out questions and repeated controlled runs. Relationship closure reaches all four connected tables here, so no large-schema retrieval savings are claimed.

**How were adversarial tests executed?** 40 distinct SQL attacks exercised the actual AST policy. Rejected SQL was never sent to PostgreSQL. Real DB privilege denials and accepted queries were executed separately. No exhaustive-security claim follows from this corpus.

**What is simulated vs live?** The database, API, browser workspace, benchmarks and test execution are real. Template generation is simulated. Ollama success/timeout/invalid-output scenarios use HTTP test doubles, not inference. Docker recipes were configuration-validated but not built/run; no base images were present. No paid APIs or model downloads.

**What about prompt injection?** Prompts label question/schema as untrusted and omit row samples, but prompts are not a security guarantee. Even a fully compromised proposal must cross the AST allowlist and DB ACL boundary. Model failure is visible and never replaced by a hidden demo answer.

**How is privacy handled?** Backend history/audit retain request ID, time, provider/mode, status, latency and row count—not questions, SQL, results or credentials. The UI keeps bounded chat only in its Streamlit session. Parser warnings that echoed rejected SQL were found with a failing test and suppressed. Database administrator logs are a separate risk.

**Would you deploy this to customers?** Not as-is. Add identity authentication, tenant/row-level authorization, TLS, managed secret storage, dependency/security auditing, distributed concurrency/rate limiting, durable audit storage, multiworker session storage, load testing and an independently reviewed SQL subset. The current boundary is a local single-user synthetic demo.

## Engineering stories grounded in execution

- Existing-work preservation: baseline had 10 failures and 2 passes; failures included a missing Ollama adapter and Windows PostgreSQL child-launch errors (`0xC0000142`). The OS-level cause was not established; running the dedicated server persistently restored database tests without touching other databases.
- Security regression: the executor originally allowed an admin DSN with an otherwise read-only SELECT. A failing test drove per-connection privilege verification before the query.
- Integration regression: the first full benchmark run passed only 75/105. Date/region templates failed because SQLGlot represents boolean `And` as a function node. A minimal failing date-filter test drove a narrow allowlist correction; rerun then passed all 105 in each mode.
- Privacy regression: SQLGlot fallback warnings logged the original SQL. A test containing a synthetic sensitive marker failed, then passed after application-level warning suppression.
- UI review: an actual browser screenshot exposed dark-background/light-theme contrast issues. A Streamlit dark theme fixed the mismatch; final screenshots show real results, not mockups.

## Next work, not claimed as done

Run a local existing Ollama model with held-out questions and non-template paraphrases; broaden SQL only behind regression tests; test clean Linux/Docker installation and image digests; independent security review/fuzzing; static typing and load tests. Consult `docs/VERIFICATION.md` and actual artifacts for final counts and limitations.
