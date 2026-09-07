"""Interactive demonstration for Agnara Historical Reference Application #005.

Guides the developer step-by-step through the internal lifecycle of Agnara
execution runtime:
  create_order -> ExecutionPlan -> Invocation -> ExecutionContext -> Result

Usage:
    python app.py
"""

from __future__ import annotations

import asyncio
import time

from agnara import CapabilityId
from agnara.core.di import DIContainer
from agnara.execution import (
    ExecutionContext,
    ExecutionPlan,
    Invocation,
    InvocationStartEvent,
    InvocationTerminalEvent,
    Success,
    TelemetryHook,
    invoke,
    invoke_result,
)

import orders
from services import AUDIT_TEARDOWN_LOG


def print_banner(title: str) -> None:
    """Print a visually distinct educational section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


class ObservableTelemetryHook(TelemetryHook):
    """Educational telemetry hook recording lifecycle events in real time."""

    def __init__(self) -> None:
        self.recorded_starts: list[InvocationStartEvent] = []
        self.recorded_terminals: list[InvocationTerminalEvent] = []

    def on_invocation_start(self, event: InvocationStartEvent) -> None:
        self.recorded_starts.append(event)
        print("  [TELEMETRY] >> Invocation Started:")
        print(f"               Capability:    {event.capability_id}")
        print(f"               Tracking ID:   {event.tracking_id}")
        print(f"               Invocation ID: {event.invocation_id}")

    def on_invocation_terminal(self, event: InvocationTerminalEvent) -> None:
        self.recorded_terminals.append(event)
        print("  [TELEMETRY] << Invocation Terminated:")
        print(f"               Capability:    {event.capability_id}")
        print(f"               Tracking ID:   {event.tracking_id}")
        print(f"               Invocation ID: {event.invocation_id}")
        print(f"               Outcome:       {event.outcome}")
        duration_ms = event.duration_ns / 1_000_000
        print(f"               Duration:      {event.duration_ns:,} ns ({duration_ms:.3f} ms)")


async def main() -> None:
    print_banner("AGNARA HISTORICAL REFERENCE APPLICATION #005: agnara-execution-runtime")
    print("Misión: Visualizar el ciclo completo de ejecución en Agnara:")
    print("        create_order -> ExecutionPlan -> Invocation -> ExecutionContext -> Result")
    print("Runtime: CPython >= 3.14 | Framework: agnara==0.1.0a3 (Historical/Frozen)")

    # -------------------------------------------------------------------------
    # PHASE 1: Authoring & Registry Compilation
    # -------------------------------------------------------------------------
    print_banner("PHASE 1: DECLARATION & REGISTRY FREEZE")
    print("1. En Agnara, '@app.capability' registra la operación pero no la ejecuta.")
    print(f"   Namespace: '{orders.app.name}' | Registradas: {len(orders.app.capabilities)}")
    for cap_id in orders.app.capabilities:
        definition = orders.app.capabilities[cap_id]
        effects_str = [e.value for e in definition.effects]
        print(f"   - {cap_id}: risk={definition.risk.value}, effects={effects_str}")

    print("\n2. 'app.compile()' congela el registro (ADR 0005) en un FrozenCapabilityRegistry.")
    frozen_caps = orders.app.compile()
    print(
        f"   Registro congelado: {type(frozen_caps).__name__} "
        "(inmutable, seguro para multihilo PEP 703)"
    )

    # -------------------------------------------------------------------------
    # PHASE 2: ExecutionPlan Compilation & Dependency Analysis
    # -------------------------------------------------------------------------
    print_banner("PHASE 2: EXECUTION PLAN COMPILATION (DAG & Protected Parameters)")
    print("1. Configuramos el DIRegistry e inyectamos providers:")
    di_registry = orders.create_di_registry()
    print("   - InventoryService: @provider(scope=Scope.SINGLETON)")
    print("   - AuditSession:     @provider(scope=Scope.INVOCATION) [Generator con Teardown]")

    hook = ObservableTelemetryHook()
    cap_def = frozen_caps[CapabilityId.parse("orders.create_order")]

    print("\n2. 'ExecutionPlan.compile()' compila el DAG de dependencias y los schemas de entrada:")
    plan = ExecutionPlan.compile(
        definition=cap_def,
        registry=di_registry,
        hooks=[hook],
    )
    print(f"   - Dependencias directas (DI): {[d.__name__ for d in plan.dependencies]}")
    print(f"   - Parámetros de contexto:     {plan.context_parameters}")
    print(f"   - Parámetros protegidos:      {sorted(list(plan.protected_parameters))}")
    print(f"   - Schemas de entrada:         {list(plan.input_schemas.keys())}")
    print(f"   - Entradas requeridas:        {sorted(list(plan.required_inputs))}")

    # -------------------------------------------------------------------------
    # PHASE 3: Successful Execution Flow
    # -------------------------------------------------------------------------
    print_banner("PHASE 3: SUCCESSFUL EXECUTION FLOW")
    print("1. El transporte construye una 'Invocation' independiente de protocolo:")
    invocation = Invocation(
        capability_id=CapabilityId.parse("orders.create_order"),
        payload={
            "customer_id": "cust_alice_99",
            "item_sku": "SKU-PRO-4K",
            "quantity": 2,
        },
        metadata={"client_agent": "web-checkout-v1"},
        deadline=time.monotonic() + 5.0,
    )
    print(f"   Invocation target: {invocation.capability_id} (deadline: {invocation.deadline:.2f})")

    print("\n2. El runtime crea el 'ExecutionContext' con el contenedor DI y tracking ID:")
    container = DIContainer(di_registry)
    context = ExecutionContext(
        invocation=invocation,
        di_container=container,
        tracking_id="req-trace-101",
    )
    print(f"   ExecutionContext initialized. Remaining time: {context.remaining_time():.2f}s")

    print("\n3. Ejecutamos mediante 'invoke_result(plan, context)':")
    result = await invoke_result(plan, context)

    print(f"\n   Resultado canónico: {type(result).__name__}")
    if isinstance(result, Success):
        order = result.value
        print(f"   Order ID:     {order.order_id}")
        print(f"   Customer:     {order.customer_id}")
        print(f"   Item SKU:     {order.item_sku}")
        print(f"   Quantity:     {order.quantity}")
        print(f"   Unit Price:   ${order.unit_price:.2f}")
        print(f"   Total Price:  ${order.total_price:.2f}")
        print(f"   Order Status: {order.status.value}")
        print(f"   Context State populated: {context.state}")

    # -------------------------------------------------------------------------
    # PHASE 4: Scoped DI Lifecycle & Teardown Verification
    # -------------------------------------------------------------------------
    print_banner("PHASE 4: SCOPED DI LIFECYCLE & TEARDOWN VERIFICATION")
    print(
        "En Agnara, los providers de tipo generador (AuditSession) se gestionan con AsyncExitStack."
    )
    print("Al terminar la invocación (éxito o fallo), el runtime garantiza su teardown.")
    print(f"Sesiones cerradas en teardown log: {AUDIT_TEARDOWN_LOG}")

    # -------------------------------------------------------------------------
    # PHASE 5: Canonical Failure Modes
    # -------------------------------------------------------------------------
    print_banner("PHASE 5: CANONICAL FAILURE OUTCOMES (FailureCode)")

    # 5.1 Domain Conflict (out of stock)
    print("\n[Case 5.1] Domain Conflict: Cantidad superior al stock disponible (pide 999 unidades)")
    inv_conflict = Invocation(
        capability_id=CapabilityId.parse("orders.create_order"),
        payload={"customer_id": "cust_bob", "item_sku": "SKU-PRO-4K", "quantity": 999},
        metadata={},
    )
    ctx_conflict = ExecutionContext(inv_conflict, container, tracking_id="req-trace-102")
    res_conflict = await invoke_result(plan, ctx_conflict)
    print(f"   Outcome: {res_conflict}")

    # 5.2 Validation Error: Missing required input
    print("\n[Case 5.2] Validation Error: Falta campo obligatorio 'item_sku'")
    inv_missing = Invocation(
        capability_id=CapabilityId.parse("orders.create_order"),
        payload={"customer_id": "cust_carol", "quantity": 1},
        metadata={},
    )
    ctx_missing = ExecutionContext(inv_missing, container, tracking_id="req-trace-103")
    res_missing = await invoke_result(plan, ctx_missing)
    print(f"   Outcome: {res_missing}")

    # 5.3 Validation Error: Invalid type
    print("\n[Case 5.3] Validation Error: Tipo incorrecto (quantity='tres' en vez de int)")
    inv_badtype = Invocation(
        capability_id=CapabilityId.parse("orders.create_order"),
        payload={"customer_id": "cust_dave", "item_sku": "SKU-KB-RGB", "quantity": "tres"},
        metadata={},
    )
    ctx_badtype = ExecutionContext(inv_badtype, container, tracking_id="req-trace-104")
    res_badtype = await invoke_result(plan, ctx_badtype)
    print(f"   Outcome: {res_badtype}")

    # 5.4 Validation Error: Unexpected input
    print("\n[Case 5.4] Validation Error: Campo no declarado 'attacker_payload'")
    inv_unexpected = Invocation(
        capability_id=CapabilityId.parse("orders.create_order"),
        payload={
            "customer_id": "cust_eve",
            "item_sku": "SKU-KB-RGB",
            "quantity": 1,
            "malicious": True,
        },
        metadata={},
    )
    ctx_unexpected = ExecutionContext(inv_unexpected, container, tracking_id="req-trace-105")
    res_unexpected = await invoke_result(plan, ctx_unexpected)
    print(f"   Outcome: {res_unexpected}")

    # 5.5 Protected Parameter Collision
    print("\n[Case 5.5] Protected Parameter Collision: Inyectar parámetro protegido 'inventory'")
    inv_protected = Invocation(
        capability_id=CapabilityId.parse("orders.create_order"),
        payload={
            "customer_id": "cust_frank",
            "item_sku": "SKU-KB-RGB",
            "quantity": 1,
            "inventory": "fake",
        },
        metadata={},
    )
    ctx_protected = ExecutionContext(inv_protected, container, tracking_id="req-trace-106")
    try:
        await invoke(plan, ctx_protected)
    except Exception as e:
        print(f"   Rechazo inmediato de parámetros reservados: {type(e).__name__}: {e}")

    # 5.6 Deadline Exceeded / Timeout
    print("\n[Case 5.6] Deadline Exceeded: Invocación asíncrona que supera el deadline")
    plan_async = ExecutionPlan.compile(
        definition=frozen_caps[CapabilityId.parse("orders.process_order_async")],
        registry=di_registry,
        hooks=[hook],
    )
    loop = asyncio.get_running_loop()
    # Deadline expira a los 5ms mientras la capability tarda 20ms
    inv_timeout = Invocation(
        capability_id=CapabilityId.parse("orders.process_order_async"),
        payload={"customer_id": "cust_grace", "item_sku": "SKU-KB-RGB", "quantity": 1},
        metadata={},
        deadline=loop.time() + 0.005,
    )
    ctx_timeout = ExecutionContext(inv_timeout, container, tracking_id="req-trace-107")
    res_timeout = await invoke_result(plan_async, ctx_timeout)
    print(f"   Outcome: {res_timeout}")

    # -------------------------------------------------------------------------
    # PHASE 6: Public Contract vs Internal Details
    # -------------------------------------------------------------------------
    print_banner("PHASE 6: PUBLIC CONTRACT (invoke_result) VS INTERNAL DETAILS (invoke)")
    print("1. 'invoke()' está pensado para llamadas ergonómicas in-process:")
    print("   - Devuelve directamente el valor desempaquetado de Python.")
    print("   - Propaga las excepciones nativas de Python sin redacción.")

    print("\n2. 'invoke_result()' está pensado para adaptadores de transporte seguros:")
    print("   - Devuelve siempre CanonicalResult[T] (Success[T] o Failure).")
    print("   - Redacta errores internos no controlados a FailureCode.INTERNAL_FAILURE.")
    print("   - Nunca expone stack traces ni detalles de implementación a clientes remotos.")

    # Cleanup container singletons
    await container.aclose()
    print("\n" + "=" * 80)
    print("  DEMOSTRACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
