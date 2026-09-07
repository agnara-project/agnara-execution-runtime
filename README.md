# Agnara Historical Reference Application #005: `agnara-execution-runtime`

[![Agnara Version](https://img.shields.io/badge/agnara-0.1.0a3-blue.svg)](https://pypi.org/project/agnara/0.1.0a3/)
[![Python](https://img.shields.io/badge/python-%3E%3D3.14-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-Historical%20%2F%20Frozen-lightgrey.svg)](#frozen-status)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

> **The canonical reference application demonstrating what happens inside Agnara after declaring a capability.**
> Explains the internal mechanics of execution, dependency resolution, execution context, invocation lifecycle, telemetry hooks, and canonical outcomes using **`agnara==0.1.0a3`** on **CPython >= 3.14**.

---

## 1. Mission & Conceptual Flow

In traditional frameworks, the path between declaring a route or task and executing it is buried inside server loops, ASGI middleware pipelines, or broker workers.

In Agnara, **execution is transport-neutral and strictly decoupled from authoring**. Declaring a capability with `@app.capability` records metadata on the authoring surface; it does **not** execute or wrap the function.

This application visualizes the complete journey of an operation from raw declaration to final canonical outcome using a clean order creation workflow:

```
+───────────────────────────────────────────────────────────────────────────────────────────────────+
|                                    THE AGNARA EXECUTION LIFECYCLE                                 |
+───────────────────────────────────────────────────────────────────────────────────────────────────+

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
     # - Compiles dependency DAG (compile_dag: detects cycles / unbound providers)
     # - Classifies protected parameters (DI dependencies & ExecutionContext)
     # - Compiles input validation TypeSchemas for payload parameters
     # - Freezes telemetry hooks & verification policies
             │
             ▼
  4. INVOCATION ARRIVAL (Protocol-Neutral Request)
     inv = Invocation(
         capability_id=CapabilityId.parse("orders.create_order"),
         payload={"customer_id": "cust_101", "item_sku": "SKU-PRO-4K", "quantity": 2},
         metadata={"client_agent": "checkout-web"},
         deadline=time.monotonic() + 5.0
     )
             │
             ▼
  5. EXECUTION CONTEXT CREATION (Per-Invocation Runtime Environment)
     container = DIContainer(di_registry)
     ctx = ExecutionContext(invocation=inv, di_container=container, tracking_id="req-trace-42")
             │
             ▼
  6. RUNTIME DISPATCH (invoke / invoke_result)
     result = await invoke_result(plan, ctx)
     ┌────────────────────────────────────────────────────────────────────────┐
     │ Inside invoke / invoke_result:                                         │
     │  a. Telemetry: on_invocation_start(InvocationStartEvent)                 │
     │  b. Deadline check: asyncio.timeout_at(ctx.deadline)                   │
     │  c. Policy evaluation: ctx.principal, confirmation, scopes             │
     │  d. Payload validation: check required, reject unexpected, validate    │
     │  e. DI Resolution: async with di_container.resolve_dependencies(...)   │
     │     - Injects singleton & invocation providers                         │
     │     - Passes ctx directly to annotated context_parameters              │
     │  f. Handler execution: run sync or await async callable                │
     │  g. Teardown: AsyncExitStack tears down generator providers            │
     │  h. Telemetry: on_invocation_terminal(InvocationTerminalEvent, outcome)│
     └────────────────────────────────────────────────────────────────────────┘
             │
             ▼
  7. CANONICAL OUTCOME
     - Success(value=Order(...))
     - Failure(code=FailureCode.CONFLICT, message="Insufficient inventory", ...)
     - Failure(code=FailureCode.INVALID_INPUT, message="required input is missing", ...)
     - Failure(code=FailureCode.TIMEOUT, message="invocation deadline exceeded")
     - Failure(code=FailureCode.INTERNAL_FAILURE, message="capability invocation failed")
```

---

## 2. What This Application Teaches

1. **Construction & Compilation of `ExecutionPlan`:**
   - Why execution plans are compiled ahead of runtime invocation.
   - How `ExecutionPlan.compile` inspects handler signatures, resolves dependencies in `DIRegistry`, detects cycles via `compile_dag`, compiles input `TypeSchema` objects, and protects DI/context parameters.
2. **Creation & Purpose of `ExecutionContext`:**
   - How `ExecutionContext` represents the active, isolated environment for a single execution.
   - How it holds the transport `Invocation`, the `DIContainer`, correlation `tracking_id`, caller `principal`, and isolated `state`.
   - How deadline and remaining time math (`ctx.remaining_time()`) are calculated.
3. **Lifecycle of an `Invocation`:**
   - How `Invocation` acts as a protocol-neutral request (`capability_id`, `payload`, `metadata`, `deadline`).
   - How `TelemetryHook` observes lifecycle transitions (`on_invocation_start` -> `on_invocation_terminal`) paired by unique runtime `invocation_id` with nanosecond precision.
4. **Dependency Resolution & Scoped Lifecycles:**
   - How `DIRegistry` binds providers and `DIContainer` resolves them.
   - The distinction between `Scope.SINGLETON` (persisted in container) and `Scope.INVOCATION` (fresh per execution).
   - How generator providers (`Iterator[T]` or `AsyncIterator[T]`) guarantee resource cleanup (e.g. database sessions, audit logs) via `AsyncExitStack` upon completion or failure.
5. **Correct Execution Mechanics:**
   - How Agnara executes both synchronous callables and `async def` coroutines with identical semantics.
   - How parameter matching divides arguments into DI dependencies, runtime context, and validated payload inputs.
6. **Success & Failure Outcomes:**
   - How `Success[T]` wraps domain return values.
   - How domain logic and framework validations yield explicit `Failure` with immutable details.
7. **Canonical Errors & Redaction Boundary:**
   - How `invoke_result()` projects errors into standardized `FailureCode` values (`INVALID_INPUT`, `TIMEOUT`, `FORBIDDEN`, `CONFLICT`, `INTERNAL_FAILURE`).
   - Why unexpected exceptions are redacted to prevent sensitive stack trace and infrastructure leakage to remote transports.
8. **Public Contract vs Internal Details:**
   - The boundary between public authoring (`Agnara`), execution (`agnara.execution`), and DI internals (`agnara.core.di`).

---

## 3. Historical Baseline & Version Pinning

| Dimension | Specification |
|---|---|
| **Framework Version** | Strictly pinned to **`agnara==0.1.0a3`** |
| **Python Runtime** | **CPython >= 3.14** (designed for lock-free free-threaded execution under PEP 703) |
| **Repository Status** | **Historical / Frozen** |
| **Public API Scope** | Uses exclusively real public exports available in `0.1.0a3`; no speculative or post-a3 APIs |

<a id="frozen-status"></a>
> [!WARNING]
> **Historical / Frozen Baseline:**
> This repository is **Agnara Historical Reference Application #005**, intentionally version-bound to **`agnara==0.1.0a3`** on **CPython >= 3.14** and must **not** be modernized to newer Agnara APIs. It preserves the exact execution runtime semantics, compilation behavior, and dependency injection mechanics of that release. Pull requests upgrading framework versions or introducing external dependencies will not be accepted.

---

## 4. Quick Start (Under 2 Minutes)

### Prerequisites
- **CPython >= 3.14**
- **PowerShell**, **Bash**, or **Zsh**

### Reproduction Steps

```powershell
# 1. Clone the repository
git clone https://github.com/agnara-project/agnara-execution-runtime.git
cd agnara-execution-runtime

# 2. Create virtual environment with Python 3.14
py -3.14 -m venv .venv

# 3. Activate the virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
# source .venv/bin/activate

# 4. Install exact pinned dependencies and editable project with dev tools
pip install -r requirements.txt
pip install -e ".[dev]"

# 5. Run the interactive demonstration
python app.py

# 6. Run the comprehensive test suite
pytest -v

# 7. Verify code quality & formatting
ruff check .
ruff format --check .

# 8. Verify package wheel build
pip wheel . --no-deps -w dist
Remove-Item -Recurse -Force dist
```

---

## 5. Architectural Breakdown: Public Contract vs Internal Details

In `agnara==0.1.0a3`, runtime execution is organized across distinct layers:

| Layer | Component | Public in a3? | Purpose |
|---|---|---|---|
| **Authoring** | `Agnara("<name>")` | :white_check_mark: Yes (`agnara`) | Namespace root and capability declaration surface. |
| **Authoring** | `@app.capability` | :white_check_mark: Yes (`agnara`) | Decorator recording declaration. Returns original callable untouched. |
| **Authoring** | `app.compile()` | :white_check_mark: Yes (`agnara`) | Freezes capability registration into immutable `FrozenCapabilityRegistry`. |
| **Execution** | `ExecutionPlan` | :white_check_mark: Yes (`agnara.execution`) | Compiled capability plan. Created via `ExecutionPlan.compile(...)`. |
| **Execution** | `Invocation` | :white_check_mark: Yes (`agnara.execution`) | Protocol-neutral execution request (`capability_id`, `payload`, `metadata`, `deadline`). |
| **Execution** | `ExecutionContext` | :white_check_mark: Yes (`agnara.execution`) | Per-invocation runtime context (`invocation`, `di_container`, `tracking_id`, `state`). |
| **Execution** | `invoke` | :white_check_mark: Yes (`agnara.execution`) | In-process execution propagating native Python return values and exceptions. |
| **Execution** | `invoke_result` | :white_check_mark: Yes (`agnara.execution`) | Transport execution returning `CanonicalResult[T]` with exception redaction. |
| **Execution** | `Success`, `Failure`, `FailureCode` | :white_check_mark: Yes (`agnara.execution`) | Semantic outcome types and standardized failure categories. |
| **Observability** | `TelemetryHook` | :white_check_mark: Yes (`agnara.execution`) | Protocol for synchronous observers (`on_invocation_start`, `on_invocation_terminal`). |
| **Dependency Injection** | `DIRegistry`, `DIContainer` | :warning: Core (`agnara.core.di`) | DI engine managing singleton caches, invocation scopes, and teardown. |
| **Dependency Injection** | `@provider(scope=...)` | :warning: Core (`agnara.core.di`) | Provider decorator defining scoped services (`Scope.SINGLETON`, `Scope.INVOCATION`). |

### Initially Proposed Capabilities Discarded in `0.1.0a3`:
1. **`app.execute(...)` or `app.invoke(...)` on `Agnara`:**
   - *Discarded because:* The `Agnara` class in `0.1.0a3` is strictly an authoring surface. It owns no execution loop or transport server (`ARCHITECTURE.md` Section 5 warns against god objects). Execution belongs to `agnara.execution.invoke` / `invoke_result`.
2. **`app.provider(...)` or built-in DI on `Agnara`:**
   - *Discarded because:* In `0.1.0a3`, DI is decoupled into `agnara.core.di`. Providers are registered into a `DIRegistry` and passed to `ExecutionPlan.compile` rather than declared on the `Agnara` instance.
3. **`ExecutionPlan.execute()` method:**
   - *Discarded because:* `ExecutionPlan` is an immutable dataclass. Execution is performed by the runtime functions `invoke(plan, context)` and `invoke_result(plan, context)`.

---

## 6. The 7 Execution Phases Demonstrated in `app.py`

When running `python app.py`, the CLI guides the developer through 7 stages:

1. **Phase 1: Declaration & Registry Freeze:**
   - Declares `orders.create_order` and `orders.cancel_order`.
   - Freezes registry into `FrozenCapabilityRegistry` (ADR 0005).
2. **Phase 2: Execution Plan Compilation:**
   - Binds `InventoryService` (Singleton) and `AuditSession` (Invocation-scoped generator).
   - Compiles `ExecutionPlan`, analyzing parameters into DI dependencies, context parameters, protected parameters, and input schemas.
3. **Phase 3: Successful In-Flight Invocation:**
   - Dispatches `Invocation` through `ExecutionContext` using `invoke_result`.
   - Produces `Success[Order]` with inventory reserved and tracking ID propagated.
4. **Phase 4: Scoped DI Lifecycle & Teardown Verification:**
   - Demonstrates how generator providers clean up resources in `finally` blocks via `AsyncExitStack`.
5. **Phase 5: Canonical Failure Outcomes:**
   - **Case 5.1 (Domain Conflict):** Insufficient inventory returns `FailureCode.CONFLICT` with structured details.
   - **Case 5.2 (Missing Input):** Missing `item_sku` returns `FailureCode.INVALID_INPUT`.
   - **Case 5.3 (Invalid Type):** String `quantity` returns `FailureCode.INVALID_INPUT`.
   - **Case 5.4 (Unexpected Input):** Undeclared payload field returns `FailureCode.INVALID_INPUT`.
   - **Case 5.5 (Protected Collision):** Payload attempting to supply `inventory` raises `InvocationError`.
   - **Case 5.6 (Deadline Exceeded):** Async capability exceeding its deadline returns `FailureCode.TIMEOUT`.
6. **Phase 6: Public Contract vs Internal Details:**
   - Compares raw `invoke()` (raises Python exceptions) with `invoke_result()` (redacts unexpected exceptions into `FailureCode.INTERNAL_FAILURE`).

---

## 7. Sample CLI Output

```text
================================================================================
  AGNARA HISTORICAL REFERENCE APPLICATION #005: agnara-execution-runtime
================================================================================
Misión: Visualizar el ciclo completo de ejecución en Agnara:
        create_order -> ExecutionPlan -> Invocation -> ExecutionContext -> Result
Runtime: CPython >= 3.14 | Framework: agnara==0.1.0a3 (Historical/Frozen)

================================================================================
  PHASE 1: DECLARATION & REGISTRY FREEZE
================================================================================
1. En Agnara, '@app.capability' registra la operación pero no la ejecuta.
   Namespace: 'orders' | Registradas: 3
   - orders.create_order: risk=medium, effects=['database-write', 'financial-write']
   - orders.cancel_order: risk=high, effects=['database-write', 'destructive']
   - orders.process_order_async: risk=high, effects=['database-write', 'financial-write']

2. 'app.compile()' congela el registro (ADR 0005) en un FrozenCapabilityRegistry.
   Registro congelado: FrozenCapabilityRegistry (inmutable, seguro para multihilo PEP 703)

================================================================================
  PHASE 2: EXECUTION PLAN COMPILATION (DAG & Protected Parameters)
================================================================================
1. Configuramos el DIRegistry e inyectamos providers:
   - InventoryService: @provider(scope=Scope.SINGLETON)
   - AuditSession:     @provider(scope=Scope.INVOCATION) [Generator con Teardown]

2. 'ExecutionPlan.compile()' compila el DAG de dependencias y los schemas de entrada:
   - Dependencias directas (DI): ['InventoryService', 'AuditSession']
   - Parámetros de contexto:     ('ctx',)
   - Parámetros protegidos:      ['audit', 'ctx', 'inventory']
   - Schemas de entrada:         ['customer_id', 'item_sku', 'quantity']
   - Entradas requeridas:        ['customer_id', 'item_sku', 'quantity']

================================================================================
  PHASE 3: SUCCESSFUL EXECUTION FLOW
================================================================================
1. El transporte construye una 'Invocation' independiente de protocolo:
   Invocation target: orders.create_order (deadline: 366837.94)

2. El runtime crea el 'ExecutionContext' con el contenedor DI y tracking ID:
   ExecutionContext initialized. Remaining time: 5.00s

3. Ejecutamos mediante 'invoke_result(plan, context)':
  [TELEMETRY] >> Invocation Started:
               Capability:    orders.create_order
               Tracking ID:   req-trace-101
               Invocation ID: 1bf4c6d7f13b4d1ea3e7452f5b042f8c
  [TELEMETRY] << Invocation Terminated:
               Capability:    orders.create_order
               Tracking ID:   req-trace-101
               Invocation ID: 1bf4c6d7f13b4d1ea3e7452f5b042f8c
               Outcome:       success
               Duration:      295,000 ns (0.295 ms)

   Resultado canónico: Success
   Order ID:     ord_a8bb83fa31
   Customer:     cust_alice_99
   Item SKU:     SKU-PRO-4K
   Quantity:     2
   Unit Price:   $450.00
   Total Price:  $900.00
   Order Status: confirmed
   Context State populated: {'created_order_id': 'ord_a8bb83fa31'}

================================================================================
  PHASE 4: SCOPED DI LIFECYCLE & TEARDOWN VERIFICATION
================================================================================
En Agnara, los providers de tipo generador (AuditSession) se gestionan con AsyncExitStack.
Al terminar la invocación (éxito o fallo), el runtime garantiza su teardown.
Sesiones cerradas en teardown log: ['7db8f242']

================================================================================
  PHASE 5: CANONICAL FAILURE OUTCOMES (FailureCode)
================================================================================

[Case 5.1] Domain Conflict: Cantidad superior al stock disponible (pide 999 unidades)
   Outcome: Failure(code=<FailureCode.CONFLICT: 'conflict'>, message='Insufficient inventory to fulfill order', details=mappingproxy({'sku': 'SKU-PRO-4K', 'requested': 999, 'available': 8}))

[Case 5.2] Validation Error: Falta campo obligatorio 'item_sku'
   Outcome: Failure(code=<FailureCode.INVALID_INPUT: 'invalid_input'>, message='required input is missing', details=mappingproxy({'path': ('item_sku',)}))

[Case 5.3] Validation Error: Tipo incorrecto (quantity='tres' en vez de int)
   Outcome: Failure(code=<FailureCode.INVALID_INPUT: 'invalid_input'>, message='expected int, got str', details=mappingproxy({'path': ('quantity',)}))

[Case 5.4] Validation Error: Campo no declarado 'attacker_payload'
   Outcome: Failure(code=<FailureCode.INVALID_INPUT: 'invalid_input'>, message='unexpected input', details=mappingproxy({'path': ('malicious',)}))

[Case 5.5] Protected Parameter Collision: Inyectar parámetro protegido 'inventory'
   Rechazo inmediato de parámetros reservados: InvocationError: invocation payload supplies runtime-owned parameter(s): inventory

[Case 5.6] Deadline Exceeded: Invocación asíncrona que supera el deadline
   Outcome: Failure(code=<FailureCode.TIMEOUT: 'timeout'>, message='invocation deadline exceeded', details=mappingproxy({}))

================================================================================
  PHASE 6: PUBLIC CONTRACT (invoke_result) VS INTERNAL DETAILS (invoke)
================================================================================
1. 'invoke()' está pensado para llamadas ergonómicas in-process:
   - Devuelve directamente el valor desempaquetado de Python.
   - Propaga las excepciones nativas de Python sin redacción.

2. 'invoke_result()' está pensado para adaptadores de transporte seguros:
   - Devuelve siempre CanonicalResult[T] (Success[T] o Failure).
   - Redacta errores internos no controlados a FailureCode.INTERNAL_FAILURE.
   - Nunca expone stack traces ni detalles de implementación a clientes remotos.

================================================================================
  DEMOSTRACIÓN COMPLETADA EXITOSAMENTE
================================================================================
```

---

## 8. Repository Layout

```
agnara-execution-runtime/
├── .agents/skills/             # Specialized agent workflows
│   ├── agnara-runtime/SKILL.md # Runtime compilation and execution workflow
│   ├── documentation/SKILL.md  # Documentation sync and style invariants
│   └── testing/SKILL.md        # Quality gates and test invariant verification
├── .github/                    # GitHub repository automation & templates
│   ├── ISSUE_TEMPLATE/         # Bug report and doc improvement issue forms
│   ├── PULL_REQUEST_TEMPLATE.md# Pull request validation checklist
│   ├── dependabot.yml          # Dependabot configuration ignoring agnara
│   └── workflows/ci.yml        # CI workflow (Python 3.14 on Ubuntu & Windows)
├── docs/                       # Architectural and technical documentation
│   ├── execution-lifecycle.md  # Detailed 6-stage execution lifecycle specification
│   └── public-api-boundary.md  # Permitted public APIs vs internal boundaries
├── AGENTS.md                   # Operational instructions for AI coding agents
├── ARCHITECTURE.md             # Deep architectural specification of execution pipeline
├── CHANGELOG.md                # Version release history
├── CONTRIBUTING.md             # Contribution rules under Historical/Frozen status
├── LICENSE                     # Apache 2.0 License
├── README.md                   # Primary pedagogical guide (this document)
├── SECURITY.md                 # Security reporting policy
├── pyproject.toml              # Project metadata & dev tooling (pytest, ruff, hatchling)
├── requirements.txt            # Strictly pinned dependency: agnara==0.1.0a3
├── domain.py                   # Pure domain models (Order, InventoryItem) & domain exceptions
├── services.py                 # InventoryService, AuditSession, and DI providers
├── orders.py                   # Capability declarations (orders.create_order, cancel_order, etc.)
├── app.py                      # Interactive pedagogical demonstration of runtime lifecycle
└── tests/
    ├── __init__.py
    ├── test_compilation.py             # ExecutionPlan compilation & signature verification
    ├── test_context_and_invocation.py  # Invocation & ExecutionContext invariants and deadlines
    ├── test_di_resolution.py          # Scoped resolution (Singleton vs Invocation) & teardown
    ├── test_execution_outcomes.py      # invoke vs invoke_result, canonical errors, redaction
    └── test_telemetry.py               # TelemetryHook lifecycle observers & nanosecond timing
```

---

## 9. License

Licensed under the **Apache License, Version 2.0**. See [`LICENSE`](LICENSE) for details.