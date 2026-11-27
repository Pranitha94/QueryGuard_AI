# QueryGuard AI — two-minute demonstration script

## Before the timer

Follow the current README to bootstrap the dedicated synthetic PostgreSQL database and start the API and UI. Open the workspace at the documented local address. Keep `AUDIT_REPORT.md` and `TEST_RESULTS.md` available. Use the **template provider**, do not claim a local model is running. Clear only this application's session history. Rehearse the queries; do not spend the two minutes installing dependencies.

## 0:00–0:15 — Set an honest scope

**Say:** “QueryGuard AI is a guarded analytics workspace. This demo uses synthetic business data and a clearly labelled deterministic SQL-template provider. Its main engineering focus is how untrusted SQL proposals are validated and executed, not a claim of general AI accuracy.”

**Show:** Provider label, four-table dataset and execution envelope.

## 0:15–0:35 — Explain the data

**Say:** “Customers place orders, and order items connect orders to products with recorded prices and quantities. The schema explorer reads approved metadata live; it does not send customer samples to a model.”

**Do:** Open **Schema explorer**, briefly point to the relationships, then return to **Analytics workspace**.

## 0:35–1:05 — Demonstrate the complete useful path

**Do:** Select **Show revenue by category** and click **Run example**. Wait for the accepted result.

**Say:** “The template proposes a joined aggregate. SQLGlot checks its structure, functions and column lineage. PostgreSQL then runs the reviewed statement through a least-privilege role in a read-only transaction. The displayed rows are calculated by the database, not stored answers.”

**Show:** Reviewed SQL, result table, chart, observed latency and **Download safe CSV**. Do not quote a universal latency promise.

## 1:05–1:20 — Demonstrate clarification

**Do:** Submit **Show revenue**.

**Say:** “This is ambiguous. The application asks for scope rather than silently choosing a grouping or date range. This demo recognizes documented patterns; it does not understand every paraphrase.”

## 1:20–1:35 — Demonstrate refusal

**Do:** Submit **Read the admin password**.

**Say:** “This request is refused. That example is not the whole security test: an independent adversarial SQL corpus and actual database privilege tests exercise separate enforcement layers.”

## 1:35–1:50 — Show measured evidence

**Do:** Open **Evaluation lab** and point to the actual report and its provider warning.

**Say:** “Reference SQL executes independently and results are compared, including order, duplicate rows and numeric values. These are template regression measurements, not live LLM accuracy. The audit lists what ran and what could not be verified.”

## 1:50–2:00 — Close with tradeoffs

**Say:** “I would next evaluate a real local model on held-out questions and harden deployment, authentication and operational budgets. This is a tested local portfolio demonstration, not a production-ready multi-tenant service.”

## If something fails during the interview

- If the backend is unavailable, show the README startup procedure and say the live demonstration is blocked; do not present a screenshot as a successful current run.
- If a provider error appears, show the explicit error and explain that the application does not silently substitute template answers for a failed model.
- If the report is missing, run the documented evaluator before presenting metrics. Never type invented scores into slides.
- If time is short, omit the schema tab; preserve the useful query, explicit simulation disclosure and limitations.
