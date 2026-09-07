# Changelog

All notable changes to `agnara-execution-runtime` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-06

### Added
- Initial release of **Agnara Historical Reference Application #005: `agnara-execution-runtime`**.
- Pinned to `agnara==0.1.0a3` on CPython >= 3.14.
- Core order and inventory domain model in `domain.py` (`Order`, `OrderItem`, `OrderStatus`, `InventoryItem`, `InsufficientStockError`, `OrderNotFoundError`).
- Dependency injection providers in `services.py` (`InventoryService`, `AuditSession`) demonstrating singleton and invocation scopes with guaranteed generator teardown.
- Capability declarations in `orders.py` (`create_order`, `cancel_order`, `process_order_async`) demonstrating mixing of DI services, runtime `ExecutionContext`, and validated inputs.
- Step-by-step interactive demonstration script in `app.py` guiding through the 7 distinct runtime phases.
- Comprehensive test suite in `tests/`:
  - `test_compilation.py`: Plan compilation, signature analysis, parameter protection, and schema validation.
  - `test_context_and_invocation.py`: Invariants of `Invocation` and `ExecutionContext`, deadlines, and remaining time math.
  - `test_di_resolution.py`: Singleton vs invocation scopes, generator teardown on success and failure.
  - `test_execution_outcomes.py`: `invoke` vs `invoke_result`, `Success[T]`, domain `Failure`, `FailureCode` mappings, and exception redaction.
  - `test_telemetry.py`: Telemetry lifecycle observer hooks, nanosecond timing, paired invocation IDs, and error suppression.
- Architectural specification in `ARCHITECTURE.md` detailing the execution pipeline.
- Machine-readable guidance in `AGENTS.md` for autonomous agents inspecting and executing capabilities.
