from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from organizations.models import Organization
from production.models import ProductionOrderStep, ProductionOrderStepComponent
from sales.models import SalesOrderIssue, SalesOrderComponent
from warehouse.models import (
    MovementPlan,
    MovementPlanItem,
    WarehouseProductionReservation,
    WarehouseUnit,
)


ZERO = Decimal("0.000")


def _to_decimal(value) -> Decimal:
    if value is None:
        return ZERO

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def _build_available_mixed_quantity_by_item(*, inv_item_ids):
    reserved_movement_unit_ids = set(
        MovementPlanItem.objects.filter(
            plan__status=MovementPlan.Status.ACTIVE,
            is_reserved=True,
        ).values_list("warehouse_unit_id", flat=True)
    )

    available_units = WarehouseUnit.objects.select_related(
        "tolling_source_order_item",
        "tolling_source_order_item__order",
    ).filter(
        status=WarehouseUnit.Status.ON_STOCK,
        inventory_item_id__in=inv_item_ids,
    ).exclude(
        id__in=reserved_movement_unit_ids,
    ).exclude(
        production_reservations__status=WarehouseProductionReservation.Status.ACTIVE,
    )

    available_quantity_by_item = defaultdict(lambda: ZERO)

    for unit in available_units:
        if unit.source_order_item_id:
            available_quantity_by_item[unit.inventory_item_id] += _to_decimal(
                unit.quantity
            )
            continue

        if (
            unit.tolling_source_order_item_id
            and unit.tolling_source_order_item.order.organization.type == Organization.Type.CHARITY
        ):
            available_quantity_by_item[unit.inventory_item_id] += _to_decimal(
                unit.quantity
            )

    return available_quantity_by_item


def _build_available_customer_quantity_by_component(*, component_ids):
    reservation_rows = (
        WarehouseProductionReservation.objects.filter(
            sales_order_component_id__in=component_ids,
            status=WarehouseProductionReservation.Status.ACTIVE,
        ).values(
            "sales_order_component_id",
        ).annotate(
            total_quantity=Sum("quantity"),
        )
    )

    return {
        row["sales_order_component_id"]: _to_decimal(row["total_quantity"])
        for row in reservation_rows
    }


def recalculate_production_step_readiness_issues(
    *,
    inv_item_ids,
):
    inv_item_ids = list({
        int(inv_item_id)
        for inv_item_id in inv_item_ids
    })

    if not inv_item_ids:
        return {
            "checked_components": 0,
            "opened_issues": 0,
            "resolved_issues": 0,
            "recalculated_at": timezone.now(),
        }

    step_components = list(
        ProductionOrderStepComponent.objects.select_related(
            "production_order_step",
            "production_order_step__production_order",
            "production_order_step__production_order__sales_order",
            "sales_order_component",
            "inv_item",
        ).filter(
            inv_item_id__in=inv_item_ids,
            production_order_step__status__in=[
                ProductionOrderStep.Status.DRAFT,
                ProductionOrderStep.Status.CONFIRMED,
            ],
        ).order_by(
            "production_order_step__production_order_id",
            "production_order_step__sequence_number",
            "id",
        )
    )

    if not step_components:
        return {
            "checked_components": 0,
            "opened_issues": 0,
            "resolved_issues": 0,
            "recalculated_at": timezone.now(),
        }

    mixed_inv_item_ids = {
        component.inv_item_id
        for component in step_components
        if component.sales_order_component.fulfillment_mode
        == SalesOrderComponent.FulfillmentMode.MIXED
    }

    customer_component_ids = {
        component.sales_order_component_id
        for component in step_components
        if component.sales_order_component.fulfillment_mode
        == SalesOrderComponent.FulfillmentMode.CUSTOMER
    }

    mixed_available_by_item = _build_available_mixed_quantity_by_item(
        inv_item_ids=mixed_inv_item_ids,
    )
    customer_available_by_component = _build_available_customer_quantity_by_component(
        component_ids=customer_component_ids,
    )

    now = timezone.now()

    opened_issues = 0
    resolved_issues = 0
    missing_component_ids = set()

    with transaction.atomic():
        for component in step_components:
            required_quantity = _to_decimal(component.required_quantity)

            if (
                component.sales_order_component.fulfillment_mode
                == SalesOrderComponent.FulfillmentMode.CUSTOMER
            ):
                available_quantity = customer_available_by_component.get(
                    component.sales_order_component_id,
                    ZERO,
                )
            else:
                available_quantity = mixed_available_by_item.get(
                    component.inv_item_id,
                    ZERO,
                )

            missing_quantity = required_quantity - available_quantity

            if missing_quantity <= ZERO:
                resolved_issues += SalesOrderIssue.objects.filter(
                    production_order_step_component=component,
                    stage=SalesOrderIssue.Stage.PRODUCTION_STEP_CONFIRMATION,
                    issue_type=SalesOrderIssue.IssueType.STEP_COMPONENT_MISSING,
                    status=SalesOrderIssue.Status.OPEN,
                ).update(
                    status=SalesOrderIssue.Status.RESOLVED,
                    resolved_at=now,
                    last_checked_at=now,
                )
                continue

            missing_component_ids.add(component.id)

            severity = (
                SalesOrderIssue.Severity.CRITICAL
                if component.is_required_for_step_start
                else SalesOrderIssue.Severity.NON_CRITICAL
            )

            issue, created = SalesOrderIssue.objects.update_or_create(
                sales_order=component.production_order_step.production_order.sales_order,
                production_order=component.production_order_step.production_order,
                production_order_step=component.production_order_step,
                production_order_step_component=component,
                stage=SalesOrderIssue.Stage.PRODUCTION_STEP_CONFIRMATION,
                issue_type=SalesOrderIssue.IssueType.STEP_COMPONENT_MISSING,
                defaults={
                    "status": SalesOrderIssue.Status.OPEN,
                    "severity": severity,
                    "message": (
                        f"Не вистачає компонента етапу: "
                        f"{component.inv_item.internal_code} — {component.inv_item.name}"
                    ),
                    "related_inv_item": component.inv_item,
                    "related_component": component.sales_order_component,
                    "missing_quantity": missing_quantity,
                    "last_checked_at": now,
                    "resolved_at": None,
                },
            )

            if created or issue.status == SalesOrderIssue.Status.OPEN:
                opened_issues += 1

        resolved_issues += SalesOrderIssue.objects.filter(
            production_order_step_component__inv_item_id__in=inv_item_ids,
            production_order_step__status__in=[
                ProductionOrderStep.Status.DRAFT,
                ProductionOrderStep.Status.CONFIRMED,
            ],
            stage=SalesOrderIssue.Stage.PRODUCTION_STEP_CONFIRMATION,
            issue_type=SalesOrderIssue.IssueType.STEP_COMPONENT_MISSING,
            status=SalesOrderIssue.Status.OPEN,
        ).exclude(
            production_order_step_component_id__in=missing_component_ids,
        ).update(
            status=SalesOrderIssue.Status.RESOLVED,
            resolved_at=now,
            last_checked_at=now,
        )

    return {
        "checked_components": len(step_components),
        "opened_issues": opened_issues,
        "resolved_issues": resolved_issues,
        "recalculated_at": now,
    }