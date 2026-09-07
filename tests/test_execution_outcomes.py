"""Tests for invoke, invoke_result, and canonical failure outcomes."""

from __future__ import annotations

import asyncio

import pytest
from agnara import CapabilityId, InvocationError
from agnara.core.di import DIContainer
from agnara.execution import (
    ExecutionContext,
    ExecutionPlan,
    Failure,
    FailureCode,
    Invocation,
    Success,
    invoke,
    invoke_result,
)

import orders
from domain import Order, OrderStatus


def test_invoke_result_successful_order() -> None:
    """Successful invocation produces Success[Order] with verified calculations."""

    async def _run() -> None:
        _, plan, container = orders.compile_orders_plan()

        inv = Invocation(
            capability_id=CapabilityId.parse("orders.create_order"),
            payload={"customer_id": "cust_101", "item_sku": "SKU-PRO-4K", "quantity": 1},
            metadata={},
        )
        ctx = ExecutionContext(inv, container, tracking_id="tr-test-1")

        res = await invoke_result(plan, ctx)

        assert isinstance(res, Success)
        assert isinstance(res.value, Order)
        assert res.value.customer_id == "cust_101"
        assert res.value.item_sku == "SKU-PRO-4K"
        assert res.value.quantity == 1
        assert res.value.unit_price == 450.0
        assert res.value.total_price == 450.0
        assert res.value.status == OrderStatus.CONFIRMED
        assert ctx.state.get("created_order_id") == res.value.order_id
        await container.aclose()

    asyncio.run(_run())


def test_domain_failure_insufficient_stock() -> None:
    """Domain conflict produces Failure(FailureCode.CONFLICT) with immutable details."""

    async def _run() -> None:
        _, plan, container = orders.compile_orders_plan()

        inv = Invocation(
            capability_id=CapabilityId.parse("orders.create_order"),
            payload={"customer_id": "cust_102", "item_sku": "SKU-PRO-4K", "quantity": 9999},
            metadata={},
        )
        ctx = ExecutionContext(inv, container)

        res = await invoke_result(plan, ctx)

        assert isinstance(res, Failure)
        assert res.code == FailureCode.CONFLICT
        assert "Insufficient inventory" in res.message
        assert res.details["sku"] == "SKU-PRO-4K"
        assert res.details["requested"] == 9999
        await container.aclose()

    asyncio.run(_run())


def test_validation_error_missing_input() -> None:
    """Missing required input parameter yields FailureCode.INVALID_INPUT with path detail."""

    async def _run() -> None:
        _, plan, container = orders.compile_orders_plan()

        inv = Invocation(
            capability_id=CapabilityId.parse("orders.create_order"),
            payload={"customer_id": "cust_103"},  # Missing item_sku and quantity
            metadata={},
        )
        ctx = ExecutionContext(inv, container)

        res = await invoke_result(plan, ctx)

        assert isinstance(res, Failure)
        assert res.code == FailureCode.INVALID_INPUT
        assert res.message == "required input is missing"
        assert "path" in res.details
        await container.aclose()

    asyncio.run(_run())


def test_validation_error_invalid_type() -> None:
    """Wrong argument type yields FailureCode.INVALID_INPUT."""

    async def _run() -> None:
        _, plan, container = orders.compile_orders_plan()

        inv = Invocation(
            capability_id=CapabilityId.parse("orders.create_order"),
            payload={"customer_id": "cust_104", "item_sku": "SKU-PRO-4K", "quantity": "two"},
            metadata={},
        )
        ctx = ExecutionContext(inv, container)

        res = await invoke_result(plan, ctx)

        assert isinstance(res, Failure)
        assert res.code == FailureCode.INVALID_INPUT
        assert "expected int, got str" in res.message
        assert res.details["path"] == ("quantity",)
        await container.aclose()

    asyncio.run(_run())


def test_validation_error_unexpected_input() -> None:
    """Unexpected payload argument yields FailureCode.INVALID_INPUT."""

    async def _run() -> None:
        _, plan, container = orders.compile_orders_plan()

        inv = Invocation(
            capability_id=CapabilityId.parse("orders.create_order"),
            payload={
                "customer_id": "cust_105",
                "item_sku": "SKU-PRO-4K",
                "quantity": 1,
                "extra": "malicious",
            },
            metadata={},
        )
        ctx = ExecutionContext(inv, container)

        res = await invoke_result(plan, ctx)

        assert isinstance(res, Failure)
        assert res.code == FailureCode.INVALID_INPUT
        assert res.message == "unexpected input"
        assert res.details["path"] == ("extra",)
        await container.aclose()

    asyncio.run(_run())


def test_protected_parameter_injection_rejected() -> None:
    """Supplying runtime-owned protected parameters in payload raises InvocationError."""

    async def _run() -> None:
        _, plan, container = orders.compile_orders_plan()

        inv = Invocation(
            capability_id=CapabilityId.parse("orders.create_order"),
            payload={
                "customer_id": "cust_106",
                "item_sku": "SKU-PRO-4K",
                "quantity": 1,
                "inventory": "fake",
            },
            metadata={},
        )
        ctx = ExecutionContext(inv, container)

        with pytest.raises(
            InvocationError, match="invocation payload supplies runtime-owned parameter"
        ):
            await invoke(plan, ctx)

        await container.aclose()

    asyncio.run(_run())


def test_target_mismatch_rejected() -> None:
    """Invocation targeting a different capability ID than plan raises InvocationError."""

    async def _run() -> None:
        _, plan, container = orders.compile_orders_plan()

        inv = Invocation(
            capability_id=CapabilityId.parse("orders.cancel_order"),
            payload={},
            metadata={},
        )
        ctx = ExecutionContext(inv, container)

        with pytest.raises(InvocationError, match="invocation targets"):
            await invoke(plan, ctx)

        await container.aclose()

    asyncio.run(_run())


def test_deadline_timeout_outcome() -> None:
    """Async capability exceeding its deadline returns FailureCode.TIMEOUT."""

    async def _run() -> None:
        frozen, _, container = orders.compile_orders_plan()
        di_reg = orders.create_di_registry()
        plan_async = ExecutionPlan.compile(
            definition=frozen[CapabilityId.parse("orders.process_order_async")],
            registry=di_reg,
        )
        loop = asyncio.get_running_loop()

        inv = Invocation(
            capability_id=CapabilityId.parse("orders.process_order_async"),
            payload={"customer_id": "cust_timeout", "item_sku": "SKU-KB-RGB", "quantity": 1},
            metadata={},
            deadline=loop.time() + 0.002,  # 2ms deadline, function takes 20ms
        )
        ctx = ExecutionContext(inv, container)

        res = await invoke_result(plan_async, ctx)

        assert isinstance(res, Failure)
        assert res.code == FailureCode.TIMEOUT
        assert "invocation deadline exceeded" in res.message
        await container.aclose()

    asyncio.run(_run())


def test_raw_invoke_vs_invoke_result_exception_handling() -> None:
    """invoke() raises raw exception, while invoke_result() redacts into INTERNAL_FAILURE."""
    from agnara import Agnara
    from agnara.core.di import DIRegistry

    async def _run() -> None:
        test_app = Agnara("error_boundary")

        @test_app.capability
        def crash_me() -> str:
            raise ZeroDivisionError("division by zero internal detail")

        frozen = test_app.compile()
        di_reg = DIRegistry()
        container = DIContainer(di_reg)
        plan = ExecutionPlan.compile(frozen[CapabilityId.parse("error_boundary.crash_me")], di_reg)

        inv = Invocation(plan.definition.id, {}, {})
        ctx = ExecutionContext(inv, container)

        # invoke() propagates the raw ZeroDivisionError
        with pytest.raises(ZeroDivisionError, match="division by zero internal detail"):
            await invoke(plan, ctx)

        # invoke_result() catches it, redacting details to prevent sensitive leakage
        res = await invoke_result(plan, ctx)
        assert isinstance(res, Failure)
        assert res.code == FailureCode.INTERNAL_FAILURE
        assert res.message == "capability invocation failed"
        assert "division by zero" not in str(res)

        await container.aclose()

    asyncio.run(_run())
