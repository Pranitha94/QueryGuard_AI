# Executed evaluation

Generated: 2026-11-26T15:22:51.394902+00:00

SIMULATED / TEMPLATE (not an LLM)

Reference SQL independently executed as least-privilege reader; typed rows, 1e-6 numeric tolerance, ordered sequence or multiset comparison. No model answer-key lookup.

|Mode|Passed / total|SQL valid / queries|Execution correct|Nonquery correct|Mean ms|p95 ms|
|---|---|---|---|---|---|---|
|baseline|105/105|78/78|78|27/27|120.715|223.225|
|schema-aware|105/105|78/78|78|27/27|119.664|221.658|

Adversarial policy rejections: {'total': 40, 'rejected': 40, 'skipped': 0}

Baseline/schema-aware results do not measure prompt improvements: the template provider ignores prompt text.

No cases skipped. No live LLM or Docker run. SQL attacks rejected before execution; privilege denials are separately tested against PostgreSQL. See evaluation.json for typed per-case results and fixture hashes.
