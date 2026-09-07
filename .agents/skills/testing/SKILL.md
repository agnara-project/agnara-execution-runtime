---
name: testing
description: Guide for verifying execution plans, DI resolution, telemetry hooks, and canonical failure outcomes.
---

# Testing Skill

Use this skill when authoring, running, or verifying tests in **Agnara Historical Reference Application #005 (`agnara-execution-runtime`)**.

---

## 1. When to Use This Skill

Activate this skill whenever:
- Adding tests for new runtime scenarios, failure modes, or DI providers.
- Verifying the integrity of `ExecutionPlan.compile` signature analysis.
- Auditing `DIContainer` scoped caching and generator provider teardown.
- Running quality gates prior to PR submission or freeze readiness checks.

---

## 2. Relevant Inputs

- **`tests/test_compilation.py`:** Tests covering plan compilation, signature validation, protected parameters, and schema building.
- **`tests/test_context_and_invocation.py`:** Tests covering `Invocation` dataclass rules and `ExecutionContext` deadline math.
- **`tests/test_di_resolution.py`:** Tests covering singleton/invocation scopes and generator teardown on success/failure.
- **`tests/test_execution_outcomes.py`:** Tests covering `invoke` vs `invoke_result`, `Success`, `Failure`, `FailureCode`, and exception redaction.
- **`tests/test_telemetry.py`:** Tests covering `TelemetryHook` lifecycle observers, timing, and error isolation.

---

## 3. Ordered Implementation Workflow

### Step 1: Unit Test Authoring Invariants
1. Use native `asyncio.run(_run())` within synchronous test functions rather than external async test runner plugins.
2. Verify both the success path and all canonical failure paths (`CONFLICT`, `INVALID_INPUT`, `TIMEOUT`, `INTERNAL_FAILURE`).
3. Ensure that container resources are always cleaned up with `await container.aclose()`.

### Step 2: Quality Gate Execution
Execute the standard 5-step verification palette:
```powershell
# 1. Code format verification
ruff format --check .

# 2. Code linting
ruff check .

# 3. Unit test suite
pytest -v

# 4. End-to-end smoke execution
python app.py

# 5. Packaging wheel verification
pip wheel . --no-deps -w dist
Remove-Item -Recurse -Force dist
```

---

## 4. Operational Boundaries & Negative Constraints

- **No Artificial Mocks:** Do not introduce `unittest.mock` or external network mocks. Use real in-memory domain services and real `DIRegistry` / `DIContainer` instances.
- **No Test Dependencies Beyond Pytest:** Do not add `pytest-asyncio` or other framework wrappers. Keep dependencies strictly minimal.

---

## 5. Validations & Definition of Done

Testing verification is complete when:
- [ ] All 5 quality gate commands exit with return code `0`.
- [ ] Pytest executes without any skipped, failed, or warning tests.
- [ ] Smoke test `python app.py` finishes with `DEMOSTRACIÓN COMPLETADA EXITOSAMENTE`.
