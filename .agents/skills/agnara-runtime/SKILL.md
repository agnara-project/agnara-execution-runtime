---
name: agnara-runtime
description: Guide for compiling execution plans, resolving scoped dependencies, constructing invocations, and executing capabilities in Agnara 0.1.0a3.
---

# Agnara Runtime Skill

Use this skill when inspecting, authoring, compiling, or executing capabilities through the Agnara runtime in **Agnara Historical Reference Application #005 (`agnara-execution-runtime`)**.

---

## 1. When to Use This Skill

Activate this skill whenever:
- Compiling an `ExecutionPlan` from a `FrozenCapabilityRegistry`.
- Configuring dependency injection providers via `DIRegistry` and resolving them with `DIContainer`.
- Constructing protocol-neutral `Invocation` requests with payloads, metadata, or monotonic deadlines.
- Initializing `ExecutionContext` with tracking correlation IDs and isolated per-invocation state.
- Executing plans via `invoke()` or `invoke_result()`.
- Observing execution lifecycle events through `TelemetryHook`.

---

## 2. Relevant Inputs

- **`CapabilityDefinition`:** Declaration extracted from `FrozenCapabilityRegistry`.
- **`DIRegistry`:** Configured dependency injection registry binding service types to `@provider` definitions.
- **`Invocation`:** Request specifying `capability_id`, `payload` dictionary, `metadata` dictionary, and optional `deadline`.
- **`ExecutionContext`:** Runtime container binding invocation, container, `tracking_id`, and `state`.

---

## 3. Ordered Implementation Workflow

### Step 1: Registry Freezing & DI Binding
1. Define services and mark providers with `@provider(scope=Scope.SINGLETON | Scope.INVOCATION)`.
2. Populate `DIRegistry` with `registry.bind(Type, provider_func)`.
3. Freeze the capability registry using `frozen = app.compile()`.

### Step 2: Plan Compilation
1. Compile the plan:
   ```python
   plan = ExecutionPlan.compile(
       definition=frozen[cap_id],
       registry=di_registry,
       hooks=telemetry_hooks,
   )
   ```
2. Verify that:
   - DI dependencies appear in `plan.dependencies`.
   - Context parameters appear in `plan.context_parameters`.
   - Protected parameters encompass both DI and context arguments.
   - Input schemas are compiled for all remaining parameters.

### Step 3: Invocation Dispatch
1. Construct the `Invocation`:
   ```python
   inv = Invocation(
       capability_id=cap_id,
       payload=payload_dict,
       metadata=metadata_dict,
       deadline=monotonic_deadline,
   )
   ```
2. Construct the `ExecutionContext`:
   ```python
   ctx = ExecutionContext(
       invocation=inv,
       di_container=DIContainer(di_registry),
       tracking_id=tracking_id,
   )
   ```

### Step 4: Execution & Outcome Inspection
1. Call `invoke_result(plan, ctx)` for safe canonical result handling:
   - Inspect `isinstance(result, Success)` vs `isinstance(result, Failure)`.
   - Check `result.code` (`FailureCode.CONFLICT`, `FailureCode.INVALID_INPUT`, `FailureCode.TIMEOUT`, etc.).
2. Call `invoke(plan, ctx)` only when direct Python exception propagation is required.
3. Clean up container singletons with `await container.aclose()`.

---

## 4. Operational Boundaries & Negative Constraints

- **Do NOT invent `app.execute()` or `app.invoke()`:** The authoring surface `Agnara` owns no execution loop.
- **Do NOT invent `app.provider()`:** Providers are bound directly to `DIRegistry`.
- **Do NOT call `plan.execute()`:** Plans are immutable data objects; pass them to `invoke()` or `invoke_result()`.
- **Do NOT inject protected parameters via payload:** Payloads supplying DI or context parameters fail immediately with `InvocationError`.

---

## 5. Validations & Definition of Done

The runtime workflow is complete when:
- [ ] `ExecutionPlan.compile` executes without `DefinitionError` or `DependencyCycleError`.
- [ ] Direct invocation yields `Success[T]` with valid payload inputs and resolved dependencies.
- [ ] Invalid inputs return canonical `Failure(FailureCode.INVALID_INPUT)`.
- [ ] Generator providers execute teardown blocks upon completion or failure.
- [ ] Telemetry hooks capture matching start and terminal events paired by `invocation_id`.
