"""Tests for TelemetryHook lifecycle observers."""

from __future__ import annotations

import asyncio

from agnara import CapabilityId
from agnara.execution import (
    ExecutionContext,
    ExecutionPlan,
    Invocation,
    InvocationStartEvent,
    InvocationTerminalEvent,
    TelemetryHook,
    invoke_result,
)

import orders


class CapturingTelemetryHook(TelemetryHook):
    """Captures start and terminal events for verification."""

    def __init__(self) -> None:
        self.starts: list[InvocationStartEvent] = []
        self.terminals: list[InvocationTerminalEvent] = []

    def on_invocation_start(self, event: InvocationStartEvent) -> None:
        self.starts.append(event)

    def on_invocation_terminal(self, event: InvocationTerminalEvent) -> None:
        self.terminals.append(event)


class FailingTelemetryHook(TelemetryHook):
    """Simulates a hook that throws an exception to test runtime isolation."""

    def on_invocation_start(self, event: InvocationStartEvent) -> None:
        raise RuntimeError("Telemetry collector crashed on start")

    def on_invocation_terminal(self, event: InvocationTerminalEvent) -> None:
        raise RuntimeError("Telemetry collector crashed on terminal")


def test_telemetry_lifecycle_events_paired_by_invocation_id() -> None:
    """Start and terminal events are emitted and paired by unique invocation_id."""

    async def _run() -> None:
        hook = CapturingTelemetryHook()
        frozen, _, container = orders.compile_orders_plan()
        di_reg = orders.create_di_registry()
        cap_id = CapabilityId.parse("orders.create_order")

        plan = ExecutionPlan.compile(frozen[cap_id], di_reg, hooks=[hook])

        inv = Invocation(
            capability_id=cap_id,
            payload={"customer_id": "cust_tel_1", "item_sku": "SKU-KB-RGB", "quantity": 1},
            metadata={"client": "test"},
        )
        ctx = ExecutionContext(inv, container, tracking_id="tr-tel-100")

        result = await invoke_result(plan, ctx)
        assert result.value is not None

        assert len(hook.starts) == 1
        assert len(hook.terminals) == 1

        start_event = hook.starts[0]
        terminal_event = hook.terminals[0]

        assert start_event.capability_id == cap_id
        assert start_event.tracking_id == "tr-tel-100"
        assert len(start_event.invocation_id) > 0

        assert terminal_event.capability_id == cap_id
        assert terminal_event.tracking_id == "tr-tel-100"
        assert terminal_event.invocation_id == start_event.invocation_id
        assert terminal_event.outcome == "success"
        assert terminal_event.duration_ns > 0
        await container.aclose()

    asyncio.run(_run())


def test_telemetry_terminal_outcome_on_validation_failure() -> None:
    """Validation failure emits terminal event with outcome='failure'."""

    async def _run() -> None:
        hook = CapturingTelemetryHook()
        frozen, _, container = orders.compile_orders_plan()
        di_reg = orders.create_di_registry()
        cap_id = CapabilityId.parse("orders.create_order")

        plan = ExecutionPlan.compile(frozen[cap_id], di_reg, hooks=[hook])

        inv = Invocation(
            capability_id=cap_id,
            payload={"customer_id": "cust_missing"},  # Missing required fields
            metadata={},
        )
        ctx = ExecutionContext(inv, container)

        await invoke_result(plan, ctx)

        assert len(hook.starts) == 1
        assert len(hook.terminals) == 1
        assert hook.terminals[0].outcome == "failure"
        await container.aclose()

    asyncio.run(_run())


def test_telemetry_exceptions_suppressed_by_runtime() -> None:
    """Exceptions raised inside telemetry hooks do not interrupt capability execution."""

    async def _run() -> None:
        hook = FailingTelemetryHook()
        frozen, _, container = orders.compile_orders_plan()
        di_reg = orders.create_di_registry()
        cap_id = CapabilityId.parse("orders.create_order")

        plan = ExecutionPlan.compile(frozen[cap_id], di_reg, hooks=[hook])

        inv = Invocation(
            capability_id=cap_id,
            payload={"customer_id": "cust_ok", "item_sku": "SKU-KB-RGB", "quantity": 1},
            metadata={},
        )
        ctx = ExecutionContext(inv, container)

        # Must succeed cleanly despite telemetry hook crashing!
        result = await invoke_result(plan, ctx)
        assert result.value is not None
        await container.aclose()

    asyncio.run(_run())
