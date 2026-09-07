# Architecture — Agnara Execution Runtime Mechanics

This document specifies the architectural principles and runtime lifecycle implemented in **Agnara Historical Reference Application #005 (`agnara-execution-runtime`)**, based on `agnara==0.1.0a3` and CPython >= 3.14.

---

## 1. Decoupled Declaration vs Execution

Traditional frameworks bind handlers directly to their execution engine:
- In Flask/FastAPI, `@app.get(...)` binds routing, validation, and request parsing directly to the ASGI/WSGI server.
- In Celery, `@task` binds execution to a queue broker and worker loop.

**In Agnara, authoring and execution are strictly separated:**
1. **Authoring Surface (`Agnara`):** Owns the logical namespace and a `CapabilityRegistry`. The `@app.capability` decorator returns the underlying callable unaltered (zero decorator distortion). It owns no server, no transport, and no execution logic.
2. **Execution Engine (`agnara.execution`):** Operates on compiled, immutable data structures (`ExecutionPlan`, `Invocation`, `ExecutionContext`) and executes handlers independently of any transport or network protocol.

---

## 2. The Conceptual Execution Lifecycle

Every capability execution traverses 5 conceptual stages:

```
+---------------------------------------------------------------------------------------------------+
|                                  THE AGNARA EXECUTION LIFECYCLE                                    |
+---------------------------------------------------------------------------------------------------+

 1. DECLARATION (Authoring Surface)
    @app.capability(risk=Risk.MEDIUM, effects=[StandardEffect.DATABASE_WRITE])
    def create_order(...) -> Order | Failure: ...
            │
            ▼
 2. REGISTRY FREEZE (Compilation Phase 1 - ADR 0005)
    frozen_registry = app.compile()  # FrozenCapabilityRegistry
            │
            ▼
 3. PLAN COMPILATION (Compilation Phase 2)
    plan = ExecutionPlan.compile(frozen_registry["orders.create_order"], di_registry, hooks=[...])
    # - Compiles DI DAG (detects cycles / unbound dependencies)
    # - Classifies protected parameters (DI dependencies & ExecutionContext)
    # - Compiles input TypeSchemas for payload parameters
    # - Freezes telemetry hooks & policies
            │
            ▼
 4. INVOCATION DISPATCH (Protocol-Neutral Request)
    inv = Invocation(
        capability_id=CapabilityId.parse("orders.create_order"),
        payload={"customer_id": "cust_101", "item_sku": "SKU-PRO-4K", "quantity": 2},
        metadata={"client": "web-checkout"},
        deadline=time.monotonic() + 5.0
    )
            │
            ▼
 5. EXECUTION CONTEXT (Per-Invocation Environment)
    container = DIContainer(di_registry)
    ctx = ExecutionContext(invocation=inv, di_container=container, tracking_id="req-trace-42")
            │
            ▼
 6. RUNTIME DISPATCH (invoke / invoke_result)
    result = await invoke_result(plan, ctx)
            │
            ▼
 7. CANONICAL OUTCOME
    Success[Order]  │  Failure(code=FailureCode.CONFLICT / INVALID_INPUT / TIMEOUT / ...)
```

---

## 3. Two-Phase Compilation

Compilation occurs in two distinct, deterministic phases:

### Phase 1: Registry Freezing (ADR 0005)
`app.compile()` transitions the mutable `CapabilityRegistry` into an immutable `FrozenCapabilityRegistry`.
- Registration is permanently closed (raising `RegistryFrozenError` on subsequent write attempts).
- Lookups become read-only mapping operations safe for lock-free parallel access under PEP 703 free-threading.

### Phase 2: Execution Plan Compilation
`ExecutionPlan.compile(definition, registry, hooks=(), ...)` transforms a `CapabilityDefinition` into an `ExecutionPlan`:
- **DAG Compilation:** Invokes `compile_dag(registry, [definition.handler])` to construct the provider dependency graph. If a dependency cycle is detected, `DependencyCycleError` is raised. If a provider requires an unbound type, `DependencyResolutionError` is raised.
- **Signature Inspection:** Analyzes `get_type_hints(definition.handler)`:
  1. Types present in `DIRegistry` become **direct dependencies**.
  2. Parameters annotated with `ExecutionContext` become **context parameters**.
  3. The union of dependencies and context parameters forms **`protected_parameters`**. The runtime guarantees that incoming payloads cannot inject or overwrite these parameters.
  4. Remaining parameters are compiled into **`input_schemas`** via `StandardSchemaAdapter`. Missing type annotations or variable arguments (`*args`, `**kwargs`) raise `DefinitionError`.

---

## 4. Invocation & Execution Context

### `Invocation` (The Request Contract)
Represents a transport-neutral request to execute a capability:
- `capability_id: CapabilityId`: Must match the plan's definition ID (validated fast before execution).
- `payload: dict[str, Any]`: The raw, unvalidated caller parameters from the transport.
- `metadata: dict[str, Any]`: Optional transport metadata (e.g. headers, RPC IDs).
- `deadline: float | None`: Optional finite monotonic timestamp.

### `ExecutionContext` (The Active Execution Environment)
Represents the runtime environment for a single execution:
- `invocation`: Reference to the initiating `Invocation`.
- `di_container`: The active `DIContainer` instance.
- `tracking_id`: Optional correlation ID for distributed tracing.
- `principal`: The calling entity (defaults to `AnonymousPrincipal()`).
- `state: dict[str, Any]`: Isolated mutable dictionary scoped strictly to this invocation for passing ephemeral data between policies, interceptors, and handlers.
- `remaining_time()`: Calculates seconds remaining against the monotonic deadline.

---

## 5. Dependency Injection & Resource Teardown

Agnara's DI system (`agnara.core.di`) supports scoped lifecycles and guaranteed cleanup:

### Provider Scopes
- **`Scope.SINGLETON`:** Cached globally in `DIContainer.singleton_cache`. Instantiated once across the lifetime of the container.
- **`Scope.INVOCATION`:** Cached per execution in `invocation_cache`. A fresh instance is created for each capability execution.

### Generator Providers & Guaranteed Teardown
Providers can be implemented as generator functions (`Iterator[T]` or `AsyncIterator[T]`):
```python
@provider(scope=Scope.INVOCATION)
def provide_audit_session() -> Iterator[AuditSession]:
    session = AuditSession()
    try:
        yield session
    finally:
        session.close()
```
When `DIContainer.resolve_dependencies` enters the execution context, it registers generator providers into an `AsyncExitStack`. When capability execution terminates—whether by returning a value, returning a Failure, raising an unhandled exception, or timing out—the exit stack is guaranteed to run all `finally` blocks.

---

## 6. Zero-Overhead Telemetry Observability (ADR 0058)

Agnara provides native lifecycle observability via `TelemetryHook`:
- `on_invocation_start(event: InvocationStartEvent)`: Emitted before dependencies are resolved.
- `on_invocation_terminal(event: InvocationTerminalEvent)`: Emitted when execution concludes, reporting `duration_ns`, `outcome` (`"success"`, `"failure"`, `"timeout"`, `"cancellation"`), and matching `invocation_id`.

### Architectural Guarantees:
1. **Zero-Cost Abstraction:** If `plan.hooks` is empty, no `uuid4()` pairing IDs are generated and no monotonic clock reads occur (saving ~2 microseconds per invocation).
2. **Pairing Integrity:** Start and terminal events share a runtime-generated `invocation_id`. Caller-supplied tracking IDs are correlation metadata, not pairing keys.
3. **Exception Isolation:** Telemetry hooks are wrapped in `with contextlib.suppress(Exception):`. A crashing telemetry collector never crashes a business transaction.

---

## 7. Canonical Outcomes & Public Error Boundaries

Agnara defines two execution functions:

| Dimension | `invoke(plan, context)` | `invoke_result(plan, context)` |
|---|---|---|
| **Intended Consumer** | In-process internal callers | Transport adapters (HTTP, MCP, CLI, RPC) |
| **Return Value** | Raw Python value `T` | `CanonicalResult[T]` (`Success[T]` or `Failure`) |
| **Domain Errors** | Returns explicit `Failure` or raises | Returns `Success[T]` or `Failure` |
| **Input Validation Errors** | Raises `ValidationError` | Returns `Failure(FailureCode.INVALID_INPUT, ...)` |
| **Deadline Timeout** | Raises `TimeoutError` | Returns `Failure(FailureCode.TIMEOUT, ...)` |
| **Unexpected Exceptions** | Propagates raw Exception (e.g. `ZeroDivisionError`) | Redacts to `Failure(FailureCode.INTERNAL_FAILURE, "capability invocation failed")` |

### The Redaction Boundary
In public transport adapters, exposing raw Python exception messages or tracebacks leaks database topologies, library versions, and internal infrastructure. `invoke_result()` enforces a strict security boundary: known semantic errors receive stable `FailureCode` values, while unknown exceptions are safely redacted into `FailureCode.INTERNAL_FAILURE`.
