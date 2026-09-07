"""Pure domain models and exceptions for order processing.

This module contains zero framework imports and represents the core business
domain: dataclasses, invariants, and domain-level exceptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class OrderStatus(StrEnum):
    """Lifecycle status of a domain order."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Order:
    """An immutable business order."""

    order_id: str
    customer_id: str
    item_sku: str
    quantity: int
    unit_price: float
    total_price: float
    status: OrderStatus
    created_at: str


@dataclass(frozen=True, slots=True)
class InventoryItem:
    """An inventory catalog item with price and stock."""

    sku: str
    name: str
    available: int
    unit_price: float


class DomainError(Exception):
    """Base exception for domain business rule violations."""


class InsufficientStockError(DomainError):
    """Raised when requested quantity exceeds available stock."""

    def __init__(self, sku: str, requested: int, available: int) -> None:
        self.sku: Final[str] = sku
        self.requested: Final[int] = requested
        self.available: Final[int] = available
        super().__init__(
            f"Insufficient stock for SKU '{sku}': requested {requested}, available {available}"
        )


class OrderNotFoundError(DomainError):
    """Raised when an order lookup fails."""

    def __init__(self, order_id: str) -> None:
        self.order_id: Final[str] = order_id
        super().__init__(f"Order '{order_id}' was not found")
