## Description

Briefly describe the change, its pedagogical objective, and why it is necessary.

---

## Historical Baseline Confirmation

This repository is **Agnara Historical Reference Application #005**, pinned to `agnara==0.1.0a3` on **CPython >= 3.14**.

- [ ] I confirm this PR does NOT upgrade `agnara`.
- [ ] I confirm this PR does NOT introduce speculative APIs from unreleased branches (`main`/`develop`).
- [ ] I confirm this PR does NOT add web frameworks, database ORMs, external network drivers, or LLM SDKs.
- [ ] I confirm execution semantics (`ExecutionPlan`, `ExecutionContext`, `Invocation`, `invoke_result`) remain strictly preserved.

---

## Scope of Changes

- [ ] Core execution runtime logic, capability declarations, or domain services
- [ ] Documentation (`README.md`, `ARCHITECTURE.md`, `docs/`, `AGENTS.md`)
- [ ] Test coverage (`tests/`)
- [ ] Packaging or CI automation (`pyproject.toml`, `.github/`)
- [ ] Agent skills (`.agents/skills/`)

---

## Definition of Done (DoD) Checklist

- [ ] `pytest -v` exits with code `0` (all tests passing).
- [ ] `ruff check .` exits with code `0` (zero linting errors).
- [ ] `ruff format --check .` exits with code `0` (all code properly formatted).
- [ ] `python app.py` runs end-to-end and exits with code `0`.
- [ ] `pip wheel . --no-deps -w dist` builds cleanly without warnings.
- [ ] Documentation and technical contracts match the implemented behavior exactly.
