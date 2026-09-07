# Public API Surface & Boundaries in Agnara 0.1.0a3

This document explicitly defines the permitted public API surface in `agnara==0.1.0a3` for **Agnara Historical Reference Application #005 (`agnara-execution-runtime`)**, and lists all prohibited or speculative APIs.

---

## 1. Permitted Public Imports

### Execution Engine (`agnara.execution`)
- `ExecutionPlan`: Compiled capability execution metadata and dependency DAG.
- `Invocation`: Protocol-neutral execution request.
- `ExecutionContext`: Per-invocation active execution environment.
- `invoke`: In-process execution preserving native Python values and exceptions.
- `invoke_result`: Safe transport execution returning `CanonicalResult[T]` with exception redaction.
- `Success`, `Failure`, `FailureCode`: Canonical execution outcome containers.
- `TelemetryHook`, `InvocationStartEvent`, `InvocationTerminalEvent`: Structured telemetry protocol and events.

### Dependency Injection (`agnara.core.di`)
- `DIRegistry`: Registry mapping types to `ProviderDefinition`.
- `DIContainer`: Runtime container resolving scoped dependencies with `AsyncExitStack` lifecycle management.
- `provider`: Decorator marking functions or generators as providers (`Scope.SINGLETON`, `Scope.INVOCATION`).
- `Scope`: Enum defining provider lifetimes.
- `compile_dag`: DAG compiler and cycle detector.

### Authoring Surface (`agnara`)
- `Agnara`: Authoring root and capability registry owner.
- `CapabilityId`: Logical identifier (`namespace.name`).
- `CapabilityDefinition`: Declaration record.
- `FrozenCapabilityRegistry`: Read-only registry returned by `app.compile()`.
- `StandardEffect`, `Risk`, `Confirmation`, `Idempotency`: Capability metadata vocabularies.

### Error Hierarchy (`agnara.errors`)
- `AgnaraError`: Base framework exception.
- `DefinitionError`: Raised on invalid identifiers or signature definitions.
- `InvocationError`: Raised on target mismatch or protected parameter collisions.
- `ValidationError`: Raised on missing, invalid, or unexpected payload arguments.
- `RegistryFrozenError`: Raised on attempts to register post-freeze.

---

## 2. Negative Boundaries: Prohibited Anti-Patterns

To preserve historical accuracy, the following speculative anti-patterns must **never** be introduced:

| Prohibited Anti-Pattern | Why Prohibited in #005 / 0.1.0a3 |
|---|---|
| `app.execute(...)` or `app.invoke(...)` | In `0.1.0a3`, `Agnara` is purely an authoring surface. It owns no execution loop or server. Execution belongs to `agnara.execution`. |
| `app.provider(...)` or `@app.bind` | DI providers belong to `agnara.core.di.DIRegistry`. In `0.1.0a3`, `Agnara` does not expose DI registration methods. |
| `ExecutionPlan.execute()` | `ExecutionPlan` is an immutable dataclass. Execution is performed through `invoke(plan, context)` and `invoke_result(plan, context)`. |
| Modifying Pinned Versions | The project is strictly pinned to `agnara==0.1.0a3`. Upgrading to unreleased branches (`main`/`develop`) violates the historical baseline. |
| External Infrastructure | No FastAPI, Flask, Starlette, external databases, or LLM SDKs. All operations remain in-memory Python structures. |
