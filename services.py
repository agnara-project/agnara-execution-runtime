"""Domain services and dependency injection providers.

Demonstrates dependency injection in Agnara:
- Scoped providers (Singleton vs Invocation)
- Sync and generator providers
- Guaranteed resource teardown through AsyncExitStack
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from agnara.core.di import Scope, provider

from domain import InsufficientStockError, InventoryItem, OrderNotFoundError

# Global record of closed audit sessions to demonstrate and test teardown
AUDIT_TEARDOWN_LOG: list[str] = []


class InventoryService:
    """Stateful domain service managing catalog inventory and reservations."""

    def __init__(self, initial_items: dict[str, InventoryItem] | None = None) -> None:
        if initial_items is not None:
            self._stock = dict(initial_items)
        else:
            self._stock = {
                "SKU-PRO-4K": InventoryItem(
                    sku="SKU-PRO-4K",
                    name="Pro 4K UltraHD Monitor",
                    available=10,
                    unit_price=450.0,
                ),
                "SKU-KB-RGB": InventoryItem(
                    sku="SKU-KB-RGB",
                    name="Mechanical Gaming Keyboard RGB",
                    available=25,
                    unit_price=85.0,
                ),
                "SKU-MOU-WL": InventoryItem(
                    sku="SKU-MOU-WL",
                    name="Wireless Ergonomic Mouse",
                    available=30,
                    unit_price=45.0,
                ),
            }

    def get_item(self, sku: str) -> InventoryItem:
        """Fetch item details or raise OrderNotFoundError."""
        item = self._stock.get(sku)
        if item is None:
            raise OrderNotFoundError(f"SKU '{sku}' not found in catalog")
        return item

    def reserve(self, sku: str, quantity: int) -> float:
        """Atomically reserve items if sufficient stock is available.

        Returns the unit price of the reserved item.
        Raises InsufficientStockError if quantity > available.
        """
        item = self.get_item(sku)
        if quantity <= 0:
            raise ValueError("Reservation quantity must be strictly positive")
        if item.available < quantity:
            raise InsufficientStockError(sku=sku, requested=quantity, available=item.available)

        updated = InventoryItem(
            sku=item.sku,
            name=item.name,
            available=item.available - quantity,
            unit_price=item.unit_price,
        )
        self._stock[sku] = updated
        return updated.unit_price

    def release(self, sku: str, quantity: int) -> None:
        """Restore inventory when an order is cancelled or rolled back."""
        item = self.get_item(sku)
        self._stock[sku] = InventoryItem(
            sku=item.sku,
            name=item.name,
            available=item.available + quantity,
            unit_price=item.unit_price,
        )


class AuditSession:
    """An invocation-scoped audit logger requiring deterministic resource teardown."""

    def __init__(self, session_id: str) -> None:
        self.session_id: str = session_id
        self.events: list[tuple[str, str]] = []
        self.is_closed: bool = False

    def record(self, action: str, details: str) -> None:
        """Record an audit entry within this session."""
        if self.is_closed:
            raise RuntimeError(f"Cannot record on closed AuditSession {self.session_id}")
        self.events.append((action, details))


@provider(scope=Scope.SINGLETON)
def provide_inventory() -> InventoryService:
    """Singleton provider: shared across all capability invocations."""
    return InventoryService()


@provider(scope=Scope.INVOCATION)
def provide_audit_session() -> Iterator[AuditSession]:
    """Invocation-scoped generator provider: fresh per invocation with teardown.

    When execution ends (on success or failure), the runtime exits the generator,
    executing the finally block and closing the session.
    """
    session_id = uuid4().hex[:8]
    session = AuditSession(session_id=session_id)
    session.record("SESSION_START", f"Opened audit session {session_id}")
    try:
        yield session
    finally:
        session.is_closed = True
        AUDIT_TEARDOWN_LOG.append(session_id)
