"""Tests for ExecutionPlan compilation and signature analysis."""

from __future__ import annotations

import pytest
from agnara import Agnara, CapabilityId, DefinitionError
from agnara.core.di import DIRegistry
from agnara.execution import ExecutionPlan

from services import AuditSession, InventoryService


def test_compile_order_execution_plan() -> None:
    """Verify standard compilation of create_order capability plan."""
    from orders import app, create_di_registry

    frozen = app.compile()
    di_reg = create_di_registry()
    cap_id = CapabilityId(namespace="orders", name="create_order")
    cap_def = frozen[cap_id]

    plan = ExecutionPlan.compile(definition=cap_def, registry=di_reg)

    assert plan.definition == cap_def
    assert InventoryService in plan.dependencies
    assert AuditSession in plan.dependencies
    assert plan.context_parameters == ("ctx",)
    assert plan.protected_parameters == frozenset({"inventory", "audit", "ctx"})
    assert set(plan.input_schemas.keys()) == {"customer_id", "item_sku", "quantity"}
    assert plan.required_inputs == frozenset({"customer_id", "item_sku", "quantity"})


def test_compile_rejects_non_capability_definition() -> None:
    """ExecutionPlan.compile must reject objects that are not CapabilityDefinition."""
    di_reg = DIRegistry()
    with pytest.raises(DefinitionError, match="definition must be a CapabilityDefinition"):
        ExecutionPlan.compile(definition="invalid", registry=di_reg)  # type: ignore[arg-type]


def test_compile_rejects_non_di_registry() -> None:
    """ExecutionPlan.compile must reject registries that are not DIRegistry."""
    from orders import app

    frozen = app.compile()
    cap_id = CapabilityId(namespace="orders", name="create_order")
    with pytest.raises(DefinitionError, match="registry must be a DIRegistry"):
        ExecutionPlan.compile(definition=frozen[cap_id], registry={})  # type: ignore[arg-type]


def test_compile_rejects_unannotated_input_parameters() -> None:
    """Capabilities with unannotated input parameters cannot be compiled into an ExecutionPlan."""
    test_app = Agnara("untyped")

    @test_app.capability
    def bad_handler(param_without_type) -> str:  # type: ignore[no-untyped-def]
        return str(param_without_type)

    frozen = test_app.compile()
    di_reg = DIRegistry()
    cap_def = frozen[CapabilityId(namespace="untyped", name="bad_handler")]

    with pytest.raises(DefinitionError, match="requires a type annotation"):
        ExecutionPlan.compile(definition=cap_def, registry=di_reg)


def test_compile_rejects_varargs_parameters() -> None:
    """Capabilities using *args or **kwargs cannot be compiled into an ExecutionPlan."""
    test_app = Agnara("varargs")

    @test_app.capability
    def varargs_handler(*args: str) -> str:
        return ",".join(args)

    frozen = test_app.compile()
    di_reg = DIRegistry()
    cap_def = frozen[CapabilityId(namespace="varargs", name="varargs_handler")]

    with pytest.raises(DefinitionError, match="must be an explicit"):
        ExecutionPlan.compile(definition=cap_def, registry=di_reg)
