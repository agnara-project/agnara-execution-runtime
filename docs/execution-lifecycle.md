# Execution Lifecycle in Agnara 0.1.0a3

This document details the exact runtime lifecycle of a capability invocation in `agnara==0.1.0a3`:
`create_order → ExecutionPlan → Invocation → ExecutionContext → Result`.

---

## 1. Lifecycle State Machine Diagram

```
       ┌───────────────────────────┐
       │   Agnara("<namespace>")   │ (Authoring Surface)
       └─────────────┬─────────────┘
                     │
                     ▼
       ┌───────────────────────────┐
       │     @app.capability       │ (Declaration Phase)
       │  - Unwrapped function     │
       │  - Invariant metadata     │
       └─────────────┬─────────────┘
                     │
                     ▼
             app.compile()           (Phase 1: Registry Freeze - ADR 0005)
                     │
                     ▼
       ┌───────────────────────────┐
       │  FrozenCapabilityRegistry │ (Read-only Capability Definitions)
       └─────────────┬─────────────┘
                     │
                     ▼
        ExecutionPlan.compile()      (Phase 2: Plan Compilation)
        - compile_dag(di_registry)
        - Detect protected params
        - Compile TypeSchemas
        - Freeze telemetry hooks
                     │
                     ▼
       ┌───────────────────────────┐
       │       ExecutionPlan       │ (Immutable Executable Metadata)
       └─────────────┬─────────────┘
                     │
                     ▼
          Invocation + Container     (Runtime Preparation)
                     │
                     ▼
       ┌───────────────────────────┐
       │     ExecutionContext      │ (Per-Invocation Environment)
       └─────────────┬─────────────┘
                     │
                     ▼
        invoke() / invoke_result()   (Runtime Dispatch)
        - on_invocation_start
        - asyncio.timeout_at
        - validate payload inputs
        - DIContainer.resolve
        - Call handler callable
        - AsyncExitStack teardown
        - on_invocation_terminal
                     │
                     ▼
       ┌───────────────────────────┐
       │      CanonicalResult      │ (Success[T] | Failure)
       └───────────────────────────┘
```

---

## 2. The 6 Detailed Stages

### Stage 1: Capability Declaration & Authoring
- `@app.capability` records the declaration in `app.capabilities`.
- Handlers are returned completely unwrapped.
- No execution logic or DI bindings exist on `app`.

### Stage 2: Registry Freeze (ADR 0005)
- `app.compile()` freezes registration permanently.
- Returns `FrozenCapabilityRegistry`.
- Any post-freeze declaration attempts raise `RegistryFrozenError`.

### Stage 3: ExecutionPlan Compilation
`ExecutionPlan.compile(definition, registry, hooks=(), ...)` compiles execution metadata:
1. **DAG Compilation (`compile_dag`):**
   - Validates that all provider dependencies exist in `DIRegistry`.
   - Traverses the dependency graph with DFS cycle detection, raising `DependencyCycleError` on recursion.
2. **Signature Classification:**
   - Detects direct DI dependencies (`immutable_deps.get(handler)`).
   - Detects `ExecutionContext` parameter annotations (`context_parameters`).
   - Merges them into `protected_parameters`.
3. **Schema Compilation (`StandardSchemaAdapter`):**
   - Compiles remaining parameters into `TypeSchema` instances.
   - Raises `DefinitionError` if parameter lacks type annotation or uses `*args`/`**kwargs`.
4. **Hook Freezing:**
   - Inspects `TelemetryHook` implementations; rejects non-callable or asynchronous callbacks.

### Stage 4: Invocation Construction
The incoming transport constructs a protocol-neutral `Invocation`:
- `capability_id: CapabilityId`: Target identifier.
- `payload: dict[str, Any]`: Unvalidated input parameters.
- `metadata: dict[str, Any]`: Transport metadata.
- `deadline: float | None`: Monotonic deadline.

### Stage 5: ExecutionContext Creation
The runtime initializes `ExecutionContext`:
- Injects the active `DIContainer`.
- Binds `tracking_id`, `principal` (defaulting to `AnonymousPrincipal()`), and `state`.
- Calculates remaining time via `ctx.remaining_time()`.

### Stage 6: Dispatch & Outcome Evaluation
`invoke(plan, ctx)` or `invoke_result(plan, ctx)` coordinates execution:
1. **Target ID Match:** Confirms `invocation.capability_id == plan.definition.id`.
2. **Protected Parameter Guard:** Fast-fails with `InvocationError` if `payload` contains any key in `plan.protected_parameters`.
3. **Telemetry Start:** Emits `InvocationStartEvent` to all hooks with generated `invocation_id`.
4. **Deadline Enforcement:** Evaluates `async with asyncio.timeout_at(ctx.deadline)`.
5. **Input Validation:** Validates payload against compiled `input_schemas`.
6. **DI Resolution:** `DIContainer.resolve_dependencies` instantiates providers.
7. **Execution:** Runs sync callable inline or awaits coroutine.
8. **Teardown:** `AsyncExitStack` guarantees execution of generator provider `finally` blocks.
9. **Telemetry Terminal:** Emits `InvocationTerminalEvent` with duration in nanoseconds and outcome status.
10. **Canonical Projection (`invoke_result`):** Projects outcome to `Success[T]` or `Failure` with redaction of unhandled exceptions.
