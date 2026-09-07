"""Tests for DIContainer lifecycle, provider scoping, and resource teardown."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

from agnara import Agnara, CapabilityId
from agnara.core.di import DIContainer, DIRegistry, Scope, provider
from agnara.execution import ExecutionContext, ExecutionPlan, Invocation, invoke_result


class CounterService:
    """Service with an internal counter to test singleton state persistence."""

    def __init__(self) -> None:
        self.count = 0

    def increment(self) -> int:
        self.count += 1
        return self.count


class RequestTracker:
    """Invocation-scoped service to test per-request isolation."""

    def __init__(self) -> None:
        self.id = uuid4().hex


class ManagedResource:
    """Resource with deterministic teardown lifecycle."""

    def __init__(self) -> None:
        self.is_open = True
        self.teardown_called = False

    def close(self) -> None:
        self.is_open = False
        self.teardown_called = True


@provider(scope=Scope.SINGLETON)
def provide_counter() -> CounterService:
    return CounterService()


@provider(scope=Scope.INVOCATION)
def provide_tracker() -> RequestTracker:
    return RequestTracker()


def test_di_singleton_persists_across_invocations() -> None:
    """Singleton-scoped providers return the identical instance across separate executions."""

    async def _run() -> None:
        app = Agnara("di_scope_test")

        @app.capability
        def track_count(counter: CounterService) -> int:
            return counter.increment()

        frozen = app.compile()
        di_reg = DIRegistry()
        di_reg.bind(CounterService, provide_counter)
        container = DIContainer(di_reg)

        plan = ExecutionPlan.compile(
            frozen[CapabilityId(namespace="di_scope_test", name="track_count")], di_reg
        )

        # First invocation
        inv1 = Invocation(plan.definition.id, {}, {})
        ctx1 = ExecutionContext(inv1, container)
        res1 = await invoke_result(plan, ctx1)
        assert res1.value == 1

        # Second invocation (same container)
        inv2 = Invocation(plan.definition.id, {}, {})
        ctx2 = ExecutionContext(inv2, container)
        res2 = await invoke_result(plan, ctx2)
        assert res2.value == 2

        await container.aclose()

    asyncio.run(_run())


def test_di_invocation_scope_is_fresh_each_run() -> None:
    """Invocation-scoped providers create a fresh instance per execution."""

    async def _run() -> None:
        app = Agnara("di_inv_test")

        @app.capability
        def get_tracker_id(tracker: RequestTracker) -> str:
            return tracker.id

        frozen = app.compile()
        di_reg = DIRegistry()
        di_reg.bind(RequestTracker, provide_tracker)
        container = DIContainer(di_reg)

        plan = ExecutionPlan.compile(
            frozen[CapabilityId(namespace="di_inv_test", name="get_tracker_id")], di_reg
        )

        inv1 = Invocation(plan.definition.id, {}, {})
        ctx1 = ExecutionContext(inv1, container)
        res1 = await invoke_result(plan, ctx1)

        inv2 = Invocation(plan.definition.id, {}, {})
        ctx2 = ExecutionContext(inv2, container)
        res2 = await invoke_result(plan, ctx2)

        assert res1.value != res2.value
        await container.aclose()

    asyncio.run(_run())


def test_di_generator_teardown_on_success() -> None:
    """Generator providers are cleanly torn down via AsyncExitStack after successful execution."""
    lifecycle_events: list[str] = []

    @provider(scope=Scope.INVOCATION)
    def provide_resource() -> Iterator[ManagedResource]:
        res = ManagedResource()
        lifecycle_events.append("setup")
        try:
            yield res
        finally:
            res.close()
            lifecycle_events.append("teardown")

    async def _run() -> None:
        app = Agnara("teardown_success")

        @app.capability
        def use_resource(res: ManagedResource) -> bool:
            assert res.is_open
            lifecycle_events.append("execute")
            return True

        frozen = app.compile()
        di_reg = DIRegistry()
        di_reg.bind(ManagedResource, provide_resource)
        container = DIContainer(di_reg)

        plan = ExecutionPlan.compile(
            frozen[CapabilityId(namespace="teardown_success", name="use_resource")], di_reg
        )

        inv = Invocation(plan.definition.id, {}, {})
        ctx = ExecutionContext(inv, container)
        result = await invoke_result(plan, ctx)

        assert result.value is True
        assert lifecycle_events == ["setup", "execute", "teardown"]
        await container.aclose()

    asyncio.run(_run())


def test_di_generator_teardown_on_failure() -> None:
    """Generator providers are guaranteed teardown even when the capability raises an exception."""
    lifecycle_events: list[str] = []

    @provider(scope=Scope.INVOCATION)
    def provide_failing_resource() -> Iterator[ManagedResource]:
        res = ManagedResource()
        lifecycle_events.append("setup")
        try:
            yield res
        finally:
            res.close()
            lifecycle_events.append("teardown_after_exception")

    async def _run() -> None:
        app = Agnara("teardown_failure")

        @app.capability
        def exploding_capability(res: ManagedResource) -> str:
            lifecycle_events.append("raise_error")
            raise RuntimeError("Database connection collapsed")

        frozen = app.compile()
        di_reg = DIRegistry()
        di_reg.bind(ManagedResource, provide_failing_resource)
        container = DIContainer(di_reg)

        plan = ExecutionPlan.compile(
            frozen[CapabilityId(namespace="teardown_failure", name="exploding_capability")], di_reg
        )

        inv = Invocation(plan.definition.id, {}, {})
        ctx = ExecutionContext(inv, container)
        result = await invoke_result(plan, ctx)

        # Internal failure returned
        assert result.code.value == "internal_failure"
        # Teardown still executed!
        assert lifecycle_events == ["setup", "raise_error", "teardown_after_exception"]
        await container.aclose()

    asyncio.run(_run())
