# Contributing to `agnara-execution-runtime`

Thank you for contributing to the Agnara Historical Reference Applications!

---

## 1. Historical Reference Status

`agnara-execution-runtime` is **Historical Reference Application #005**, strictly pinned to **`agnara==0.1.0a3`** on **CPython >= 3.14**.

Because of its historical and pedagogical mission:
- **This repository is Frozen.**
- PRs upgrading `agnara` to post-a3 versions are rejected.
- PRs introducing web frameworks, external database drivers, or unnecessary mocks are rejected.
- Only documentation improvements, pedagogical bug fixes, or test enhancements are accepted.

---

## 2. GitFlow Workflow

The repository follows a clean GitFlow model:

```
[develop] ────●────●────●────● (Validated changes & PR staging)
                            │
                            │ Pull Request (Review & Validation)
                            ▼
[main] ─────────────────────● (Historical / Frozen release baseline)
```

1. **`main` Branch:** Represents the stable, frozen historical baseline. Direct commits to `main` are strictly prohibited.
2. **`develop` Branch:** Active development branch. All feature or bugfix branches must branch from and target `develop`.
3. **Branch Naming:** Use `feature/<name>`, `fix/<name>`, or `docs/<name>`.
4. **Conventional Commits:** Use standard commit prefixes (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

---

## 3. Pull Request Process

1. Fork and clone the repository.
2. Create your branch from `develop`:
   ```bash
   git checkout -b fix/doc-clarification develop
   ```
3. Set up the development environment:
   ```powershell
   py -3.14 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```
4. Verify all quality gates:
   ```powershell
   ruff check .
   pytest -v
   python app.py
   ```
5. Submit your PR targeting the `develop` branch.
