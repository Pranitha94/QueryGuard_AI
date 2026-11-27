# Executed evaluation

Generated: 2026-11-27T08:41:53.262233+00:00

SIMULATED / TEMPLATE (not an LLM)

Reference SQL independently executed as least-privilege reader; typed rows, 1e-6 numeric tolerance, ordered sequence or multiset comparison. No model answer-key lookup.

|Mode|Passed / total|SQL valid / queries|Execution correct|Nonquery correct|Mean ms|p95 ms|
|---|---|---|---|---|---|---|
|baseline|105/105|78/78|78|27/27|107.83|207.658|
|schema-aware|105/105|78/78|78|27/27|107.762|202.704|

Adversarial policy rejections: {'total': 40, 'rejected': 40, 'skipped': 0}

Baseline/schema-aware results do not measure prompt improvements: the template provider ignores prompt text.

No cases skipped. No live LLM or Docker run. SQL attacks rejected before execution; privilege denials are separately tested against PostgreSQL. See evaluation.json for typed per-case results and fixture hashes.
