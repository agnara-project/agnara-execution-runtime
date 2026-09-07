"""Agnara capability declarations for order management.

Demonstrates:
- Declaring capabilities with rich agentic metadata (effects, risk, idempotency)
- Mixing DI-injected services, runtime-injected ExecutionContext, and payload inputs
- Explicit domain outcomes using Success and Failure
- Building immutable ExecutionPlans from the frozen registry
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import uuid4

from agnara import Agnara, CapabilityId, FrozenCapabilityRegistry, Risk, StandardEffect
from agnara.core.di import DIContainer, DIRegistry
from agnara.execution import (
    ExecutionContext,
    ExecutionPlan,
    Failure,
    FailureCode,
    TelemetryHook,
)

from domain import InsufficientStockError, Order, OrderNotFoundError, OrderStatus
from services import (
    AuditSession,
    InventoryService,
    provide_audit_session,
    provide_inventory,
)

# Composition Root: Agnara authoring application
app = Agnara("orders")


@app.capability(
    name="create_order",
    description="Reserve catalog inventory, create a domain order, and log audit trail.",
    risk=Risk.MEDIUM,
    effects=[StandardEffect.DATABASE_WRITE, StandardEffect.FINANCIAL_WRITE],
    idempotent=False,
)
def create_order(
    customer_id: str,
    item_sku: str,
    quantity: int,
    inventory: InventoryService,
    audit: AuditSession,
    ctx: ExecutionContext,
) -> Order | Failure:
    """Create a new customer order after validating and reserving inventory."""
    if quantity <= 0:
        return Failure(
            FailureCode.INVALID_INPUT,
            "Order quantity must be strictly positive",
            details={"quantity": quantity},
        )

    try:
        unit_price = inventory.reserve(item_sku, quantity)
    except InsufficientStockError as err:
        return Failure(
            FailureCode.CONFLICT,
            "Insufficient inventory to fulfill order",
            details={
                "sku": err.sku,
                "requested": err.requested,
                "available": err.available,
            },
        )
    except OrderNotFoundError as err:
        return Failure(
            FailureCode.NOT_FOUND,
            f"Catalog item not found: {err.order_id}",
            details={"sku": item_sku},
        )

    order_id = f"ord_{uuid4().hex[:10]}"
    total_price = round(unit_price * quantity, 2)
    timestamp = datetime.now(timezone.utc).isoformat()

    audit.record(
        "ORDER_RESERVED",
        f"Order {order_id} created for customer {customer_id}: {quantity}x {item_sku}",
    )

    # Store execution tracking in per-invocation context state
    ctx.state["created_order_id"] = order_id

    return Order(
        order_id=order_id,
        customer_id=customer_id,
        item_sku=item_sku,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
        status=OrderStatus.CONFIRMED,
        created_at=timestamp,
    )


@app.capability(
    name="cancel_order",
    description="Cancel a customer order, release stock back to inventory, and log audit trail.",
    risk=Risk.HIGH,
    effects=[StandardEffect.DATABASE_WRITE, StandardEffect.DESTRUCTIVE],
    idempotent=False,
)
def cancel_order(
    order_id: str,
    item_sku: str,
    quantity: int,
    inventory: InventoryService,
    audit: AuditSession,
    ctx: ExecutionContext,
) -> Order | Failure:
    """Cancel an existing order and restore reserved stock."""
    if quantity <= 0:
        return Failure(
            FailureCode.INVALID_INPUT,
            "Cancellation quantity must be positive",
            details={"quantity": quantity},
        )

    try:
        item = inventory.get_item(item_sku)
        inventory.release(item_sku, quantity)
    except OrderNotFoundError:
        return Failure(
            FailureCode.NOT_FOUND,
            f"Item SKU '{item_sku}' not found for cancellation",
            details={"sku": item_sku},
        )

    audit.record("ORDER_CANCELLED", f"Order {order_id} cancelled ({quantity}x {item_sku})")
    ctx.state["cancelled_order_id"] = order_id

    return Order(
        order_id=order_id,
        customer_id="unknown",
        item_sku=item_sku,
        quantity=quantity,
        unit_price=item.unit_price,
        total_price=round(item.unit_price * quantity, 2),
        status=OrderStatus.CANCELLED,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@app.capability(
    name="process_order_async",
    description="Asynchronously process an order with simulated payment verification.",
    risk=Risk.HIGH,
    effects=[StandardEffect.FINANCIAL_WRITE, StandardEffect.DATABASE_WRITE],
    idempotent=False,
)
async def process_order_async(
    customer_id: str,
    item_sku: str,
    quantity: int,
    inventory: InventoryService,
    audit: AuditSession,
    ctx: ExecutionContext,
) -> Order | Failure:
    """Asynchronous order processing with simulated external verification."""
    # Non-blocking async check (e.g. payment gateway or external fraud service)
    await asyncio.sleep(0.02)
    return create_order(customer_id, item_sku, quantity, inventory, audit, ctx)


def create_di_registry() -> DIRegistry:
    """Configure dependency injection bindings for order services."""
    registry = DIRegistry()
    registry.bind(InventoryService, provide_inventory)
    registry.bind(AuditSession, provide_audit_session)
    return registry


def compile_orders_plan(
    capability_name: str = "create_order",
    registry: DIRegistry | None = None,
    hooks: Sequence[TelemetryHook] = (),
) -> tuple[FrozenCapabilityRegistry, ExecutionPlan, DIContainer]:
    """Freeze registry, compile DAG and plan, and return runtime container."""
    frozen_caps = app.compile() if not app.is_compiled else app.capabilities.freeze()
    di_reg = registry if registry is not None else create_di_registry()
    container = DIContainer(di_reg)

    cap_id = CapabilityId(namespace="orders", name=capability_name)
    plan = ExecutionPlan.compile(
        definition=frozen_caps[cap_id],
        registry=di_reg,
        hooks=hooks,
    )
    return frozen_caps, plan, container
