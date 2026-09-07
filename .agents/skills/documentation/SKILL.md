---
name: documentation
description: Standards and synchronization rules for maintaining Agnara execution runtime documentation.
---

# Documentation Skill

Use this skill when reading, authoring, or updating documentation in **Agnara Historical Reference Application #005 (`agnara-execution-runtime`)**.

---

## 1. When to Use This Skill

Activate this skill whenever:
- Adding or modifying capability declarations, domain models, or DI services.
- Updating the interactive demonstration in `app.py`.
- Documenting runtime lifecycle invariants, execution stages, or error handling behavior.
- Verifying consistency across `README.md`, `ARCHITECTURE.md`, `AGENTS.md`, and `docs/`.

---

## 2. Relevant Inputs

- **`README.md`:** Human-oriented pedagogical guide.
- **`AGENTS.md`:** Machine-oriented operational contract for AI coding agents.
- **`ARCHITECTURE.md`:** Architectural deep dive into execution mechanics, DI, and telemetry.
- **`docs/execution-lifecycle.md`:** Detailed stage-by-stage lifecycle specification.
- **`docs/public-api-boundary.md`:** Inventory of supported vs prohibited APIs.
- **`CHANGELOG.md`:** Versioned release history.

---

## 3. Ordered Implementation Workflow

### Step 1: Code & Docstring Alignment
1. Verify that type annotations, parameter names, and docstrings in `domain.py`, `services.py`, and `orders.py` reflect the true implementation.
2. Ensure no speculative comments or dead explanations remain.

### Step 2: Educational Walkthrough Alignment
1. Verify that console outputs and phase descriptions in `app.py` match the implemented capabilities.

### Step 3: Documentation Synchronization
1. Keep `README.md` focused on human onboarding, quickstart, visual flowcharts, and output samples.
2. Keep `AGENTS.md` focused on agent operational rules, negative constraints, and verification palettes.
3. Keep `ARCHITECTURE.md` and `docs/` focused on deep specifications.

### Step 4: Changelog Tracking
1. Log all notable modifications in `CHANGELOG.md` under the appropriate release header following Keep a Changelog.

---

## 4. Operational Boundaries & Negative Constraints

- **No Speculative Version Claims:** Never state or imply compatibility with Agnara releases post-`0.1.0a3`.
- **No Placeholder Text:** Never leave `TODO`, `TBD`, or temporary notes in public documentation.
- **No Redundant Duplication:** Do not duplicate full sections across `README.md` and `AGENTS.md`; use cross-links instead.

---

## 5. Validations & Definition of Done

Documentation work is complete when:
- [ ] Every symbol and signature documented in markdown matches the actual code in the repository.
- [ ] Markdown files pass formatting checks with no broken relative links.
- [ ] The Historical/Frozen baseline notice is prominent across all documentation surfaces.
