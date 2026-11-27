# QueryGuard AI — project-specific interview questions

These answers describe the implemented local synthetic-data application, not a production service or a demonstrated general-purpose LLM. Verify current counts in `TEST_RESULTS.md` rather than memorizing old checkpoints.

## 1. What problem does this project solve?
It lets a user inspect an analytics question's generated SQL and returned data while demonstrating safeguards around untrusted SQL. The default is a deliberately narrow, deterministic template demo. An optional Ollama adapter can propose SQL, but live inference must be evaluated separately.

## 2. What happens after a user asks a question?
Streamlit sends JSON to FastAPI with an opaque session token. The service retrieves live allowlisted schema metadata, builds a prompt, requests a structured proposal, reviews query SQL with SQLGlot, and executes only the reviewed SQL through a restricted PostgreSQL connection. The UI renders results, an appropriate chart and a CSV control.

## 3. Is the default provider actually an AI model?
No. `TemplateProvider` recognizes documented question families and generates SQL templates. It never predicts a result value: PostgreSQL computes the answer. This is useful for a free reproducible demo but cannot establish LLM intelligence or paraphrase accuracy.

## 4. Are the displayed business totals hardcoded?
The SQL patterns and synthetic seed are deterministic, but result rows come from PostgreSQL. Hardcoded SQL is not the same as a hardcoded answer. The audit distinguishes this from a live-model evaluation and checks execution against independent reference SQL.

## 5. Why use a structured Proposal instead of parsing arbitrary model prose?
`Proposal` restricts status to query, clarification or refusal; bounds string sizes; forbids extra fields; and checks that only query status carries SQL. The model's JSON is still untrusted: satisfying Pydantic does not authorize execution.

## 6. What is SQLGlot doing here?
It parses PostgreSQL SQL into an abstract syntax tree, like a structured map of statements, tables, columns and operations. The policy can inspect nested constructs rather than rely on suspicious words appearing in a string.

## 7. Why isn't a SELECT-prefix check sufficient?
A SELECT can call an unsafe function, read system tables, contain locking clauses or wrap a dangerous operation. The project checks the whole AST against explicit node, function, type, table and column allowlists and limits the number of statements.

## 8. What is column lineage, and why does it matter?
Lineage connects a selected column back to its physical source through aliases, subqueries and CTEs. Without it, an innocuous alias could hide access to a forbidden table or column. Qualification resolves names; a second policy review checks the resolved tree.

## 9. Why review SQL both before and after qualification?
The first review rejects obviously unsupported syntax. Qualification then resolves ambiguous names against the approved schema. The second review checks what the resolver actually produced, including its table and column references; resolution is not itself permission.

## 10. Why disallow SELECT * but allow COUNT(*)?
Selecting a star can expose a newly added or unapproved column. COUNT(*) counts rows without returning every column's values. The policy makes that narrow exception rather than treating all stars as equivalent.

## 11. What kinds of SQL are supported?
The approved subset includes explicit projections, filters, equality joins, aggregates, grouping, ordering, nonrecursive CTEs, some nested queries and set operations. It intentionally does not implement every valid PostgreSQL feature. A valid query outside the subset may be safely refused.

## 12. Why have a read-only database role if the AST is already checked?
The application validator can contain bugs. PostgreSQL permissions provide a separate enforcement layer: the runtime role lacks superuser, role-membership, write and object-creation capabilities. Read-only transactions and timeouts add more layers but do not replace actual grants.

## 13. Is default_transaction_read_only enough to guarantee least privilege?
No. A sufficiently privileged connection can change transaction mode. The tests deliberately disable the default read-only setting before attempting prohibited writes or creation, so an ACL denial is tested independently from the default flag.

## 14. Why are setup and runtime credentials separate?
Setup needs permission to create tables, seed data and configure a restricted role. A request-handling API should not need that authority. Compose separates those credentials; the native demo keeps setup configuration in a private, ignored local environment file.

## 15. What does runtime privilege verification check?
It rejects powerful role flags, role memberships, database or schema creation permission, data-write privileges and missing SELECT permission on approved columns. Checks run at startup/readiness and on execution connections. This is not proof against an administrator maliciously changing the database environment.

## 16. What tables are in the synthetic business database?
Customers describe synthetic labels, regions and segments. Products have labels, categories and prices. Orders connect customers to order dates and statuses. Order items connect orders and products with quantities and historical unit prices. Foreign keys represent those relationships.

## 17. Why multiply order-item quantity by unit_price rather than today's product price?
An item's unit price represents the price recorded for that order. A product's current catalog price can change. Using recorded item prices avoids rewriting historical revenue when the catalog changes.

## 18. How do you avoid an incorrect average order value?
First aggregate item totals per order, then average those order totals. Averaging individual line-item values weights orders with more lines differently and answers a different question. The template uses a CTE for the two-stage calculation.

## 19. Does LIMIT 200 make any query cheap?
No. A database may scan, join, group or sort many rows before returning 200 results. The project also imposes a statement timeout, a lock timeout, AST complexity/depth limits and a query concurrency ceiling. There is no demonstrated production cost model.

## 20. What prevents a provider response from using unlimited memory?
The audited adapter reads the HTTP response incrementally and rejects it after its configured byte budget, closing the response. It requests identity encoding and rejects compressed responses. This is tested with an HTTP double, not a live model. Per-operation timeouts are not a strict end-to-end deadline.

## 21. What happens if Ollama returns malformed JSON or times out?
The adapter raises a sanitized `ProviderError`; orchestration returns an explicit provider_error outcome. It does not silently switch to the template provider, because that would hide a real-model failure behind a different implementation.

## 22. How does the application handle ambiguity?
A structured proposal can ask for clarification rather than choose a metric or date range silently. The deterministic demo has a documented set of ambiguous questions. It is not a general conversational clarification engine with durable multi-turn reasoning.

## 23. What does schema-aware retrieval actually achieve in this dataset?
Keyword ranking chooses relevant tables and relationship closure adds neighbors needed for joins. Since all four tables form one connected graph, closure often includes all four. That demonstrates metadata plumbing, not measured large-schema retrieval efficiency.

## 24. How is execution accuracy evaluated?
The offline evaluator executes independently authored reference SQL against the same seed, executes generated SQL through the guarded path and compares typed rows. It accounts for numeric tolerance, duplicate rows and ordering semantics rather than requiring the two SQL strings to match.

## 25. Why can baseline and schema-aware both get perfect template scores?
The deterministic provider ignores the prompt strategy. Its supported vocabulary was deliberately implemented, and the cases are a functional regression suite, not an unseen language-generalization test. Equal scores do not demonstrate that schema retrieval improves LLM accuracy.

## 26. What would be required for a credible LLM quality claim?
Run an actual identified model, record model/version/configuration, use independent held-out questions and paraphrases, preserve all refusals and failures, execute reference comparisons, and report denominators and latency. Repeat across prompt settings without selecting only successful examples.

## 27. How are security cases different from ordinary evaluation cases?
The adversarial corpus tests that forbidden SQL is rejected before it reaches PostgreSQL. Separate privilege tests demonstrate the database denies prohibited operations. Neither a finite attack corpus nor passing tests proves complete security.

## 28. Are session tokens user authentication?
No. Anyone who can reach the local API can request a session. Tokens isolate bounded history and expire; they do not identify a human, assign a role or provide production tenant authorization. The API and UI therefore default to loopback addresses.

## 29. How does the application recover from an expired browser session?
The audited UI can request a new session after a 401 and retry the rejected request once. A 401 is issued before query execution, so this does not replay a successful SQL operation. Old UI messages are cleared when the token changes.

## 30. What information is recorded in audit logs?
Only bounded request metadata such as a random request ID, time, status, mode, provider label, latency and row count. Raw questions, SQL literals, result rows, credentials and tokens are excluded. PostgreSQL's own administrator-controlled logs are a different boundary.

## 31. What happens if the audit disk path becomes unavailable?
Directory creation, size inspection, rotation and append are inside sanitized filesystem error handling. A failed audit returns a clear 503 rather than presenting an unlogged result as success. A finally block returns the concurrency slot. This is availability handling, not durable compliance logging.

## 32. Why neutralize CSV cells beginning with =, +, - or @?
Spreadsheet software may interpret such strings as formulas when a CSV is opened. Escaping unsafe text cells and headers reduces formula-execution risk. CSV escaping alone does not replace ordinary access control or protect every possible spreadsheet configuration.

## 33. How do you avoid Markdown-based data exfiltration in the UI?
Questions and provider messages are rendered as plain text instead of Markdown. Otherwise a crafted Markdown image could make a browser request an external URL. Fixed application copy may use Markdown; untrusted text is treated differently.

## 34. Which tests use real infrastructure and which use doubles?
Database, privilege, execution and API integration tests use the dedicated synthetic PostgreSQL database. Provider error/size tests and many Streamlit component tests use explicit HTTP doubles. Browser journeys exercise the running UI and API. A simulated provider test must never be described as live inference.

## 35. Why did the original UI test become unreliable?
It mixed a component-render assertion with requests to separately running services, whose latency and availability were not controlled by that test. The audit observed a timeout. The component test now uses a labelled transport double; actual UI-to-API journeys are verified separately.

## 36. How do you reproduce the project without copying the author's secrets?
Clone the repository, create a supported isolated Python environment, install its pinned requirements, then run the documented bootstrap for a new dedicated synthetic database. Generate local secrets rather than commit or reuse them. Inspect the audit's fresh-clone evidence for tested platforms and any remaining setup limitations.

## 37. What are the main architectural tradeoffs?
A small synchronous service and explicit modules are easy to explain and test. Rechecking privileges and introspecting schema on requests costs extra database round trips; per-request HTTP clients also limit pooling. That favors transparent safety for a tiny local demo over throughput. Optimize only with measured evidence and cache invalidation rules.

## 38. What would you change before any public deployment?
Add real authentication and authorization, tenant/data isolation, durable audit and session storage, a strict provider/request budget, request-body and resource controls, validated deployment configuration, dependency/image security review and operational monitoring. Re-test the broader threat model; do not merely change the bind address.

## 39. What does a passing CI workflow prove—and not prove?
It proves that the configured job succeeded for a specific commit, including only the steps that actually ran. The existing Ubuntu job installs dependencies, uses a PostgreSQL service and runs checks/evaluation. It does not prove the complete application Compose stack ran, that a real model answered questions, or that the application is production-ready.

## 40. How would you present this honestly in a hiring interview?
Lead with secure backend design, PostgreSQL permissions, AST authorization and reproducible testing. Show the working deterministic demo and disclose its narrow vocabulary before discussing optional LLM integration. Describe measured tests and limitations, explain a bug fixed during audit, and avoid invented client impact, production scale or model-accuracy claims.
