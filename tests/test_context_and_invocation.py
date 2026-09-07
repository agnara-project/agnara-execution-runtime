"""Tests for Invocation and ExecutionContext invariants."""

from __future__ import annotations

import time

import pytest
from agnara import CapabilityId, DefinitionError
from agnara.core.di import DIContainer, DIRegistry
from agnara.execution import ExecutionContext, Invocation
from agnara.policy.principal import AnonymousPrincipal


def test_invocation_valid_initialization() -> None:
    """Invocation stores capability_id, payload, metadata, and finite deadline."""
    cap_id = CapabilityId.parse("orders.create_order")
    payload = {"customer_id": "c1", "item_sku": "SKU-PRO-4K", "quantity": 1}
    metadata = {"trace": "abc"}
    now = time.monotonic()

    inv = Invocation(
        capability_id=cap_id,
        payload=payload,
        metadata=metadata,
        deadline=now + 10.0,
    )

    assert inv.capability_id == cap_id
    assert inv.payload == payload
    assert inv.metadata == metadata
    assert inv.deadline == pytest.approx(now + 10.0)


def test_invocation_rejects_string_capability_id() -> None:
    """Invocation requires a CapabilityId instance, rejecting raw strings."""
    with pytest.raises(DefinitionError, match="capability_id must be a CapabilityId"):
        Invocation(
            capability_id="orders.create_order",  # type: ignore[arg-type]
            payload={},
            metadata={},
        )


def test_invocation_rejects_non_dict_payload_or_metadata() -> None:
    """Invocation payload and metadata must be dictionaries."""
    cap_id = CapabilityId.parse("orders.create_order")

    with pytest.raises(DefinitionError, match="payload must be a dictionary"):
        Invocation(capability_id=cap_id, payload=[], metadata={})  # type: ignore[arg-type]

    with pytest.raises(DefinitionError, match="metadata must be a dictionary"):
        Invocation(capability_id=cap_id, payload={}, metadata="not_a_dict")  # type: ignore[arg-type]


def test_invocation_rejects_invalid_deadline() -> None:
    """Invocation deadline must be a finite float/int or None."""
    cap_id = CapabilityId.parse("orders.create_order")

    with pytest.raises(DefinitionError, match="deadline must be a finite monotonic timestamp"):
        Invocation(capability_id=cap_id, payload={}, metadata={}, deadline=float("inf"))

    with pytest.raises(DefinitionError, match="deadline must be a finite monotonic timestamp"):
        Invocation(capability_id=cap_id, payload={}, metadata={}, deadline=True)  # type: ignore[arg-type]


def test_execution_context_defaults_and_state() -> None:
    """ExecutionContext defaults principal to AnonymousPrincipal and provides isolated state."""
    cap_id = CapabilityId.parse("orders.create_order")
    inv = Invocation(capability_id=cap_id, payload={}, metadata={})
    container = DIContainer(DIRegistry())

    ctx = ExecutionContext(invocation=inv, di_container=container, tracking_id="tr-123")

    assert ctx.invocation == inv
    assert ctx.di_container == container
    assert ctx.tracking_id == "tr-123"
    assert isinstance(ctx.principal, AnonymousPrincipal)
    assert ctx.confirmation_evidence is None
    assert ctx.state == {}

    # Mutating per-invocation state
    ctx.state["key"] = "value"
    assert ctx.state["key"] == "value"


def test_execution_context_remaining_time() -> None:
    """ExecutionContext calculates remaining time against monotonic deadline."""
    cap_id = CapabilityId.parse("orders.create_order")
    now = 100.0

    # Without deadline
    inv_no_deadline = Invocation(capability_id=cap_id, payload={}, metadata={}, deadline=None)
    ctx_no_deadline = ExecutionContext(inv_no_deadline, DIContainer(DIRegistry()))
    assert ctx_no_deadline.remaining_time(now=now) is None

    # With future deadline
    inv_future = Invocation(capability_id=cap_id, payload={}, metadata={}, deadline=110.0)
    ctx_future = ExecutionContext(inv_future, DIContainer(DIRegistry()))
    assert ctx_future.remaining_time(now=now) == pytest.approx(10.0)

    # With past deadline (clamped to zero)
    inv_past = Invocation(capability_id=cap_id, payload={}, metadata={}, deadline=90.0)
    ctx_past = ExecutionContext(inv_past, DIContainer(DIRegistry()))
    assert ctx_past.remaining_time(now=now) == 0.0
