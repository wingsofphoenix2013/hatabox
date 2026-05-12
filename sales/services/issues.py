from decimal import Decimal

from django.utils import timezone

from sales.models import SalesOrder, SalesOrderComponent, SalesOrderIssue
from warehouse.services.production_reservation import (
    _build_available_unit_pools,
    _select_units_from_pool,
    _to_decimal,
)


ZERO = Decimal("0.000")


def recalculate_customer_component_confirmation_issues(
    *,
    organization_id,
    inv_item_id,
):
    sales_orders = list(
        SalesOrder.objects.filter(
            organization_id=organization_id,
            status=SalesOrder.Status.DRAFT,
            components__inv_item_id=inv_item_id,
            components__fulfillment_mode=SalesOrderComponent.FulfillmentMode.CUSTOMER,
        ).distinct().order_by(
            "created_at",
            "id",
        )
    )

    if not sales_orders:
        return {
            "organization_id": organization_id,
            "inv_item_id": inv_item_id,
            "checked_orders": 0,
        }

    available_unit_pools = _build_available_unit_pools(
        sales_order=sales_orders[0],
        item_ids=[inv_item_id],
    )

    available_units = available_unit_pools[inv_item_id]["customer"]
    now = timezone.now()

    checked_orders = 0
    resolved_issues = 0
    opened_issues = 0

    for sales_order in sales_orders:
        component = sales_order.components.filter(
            inv_item_id=inv_item_id,
            fulfillment_mode=SalesOrderComponent.FulfillmentMode.CUSTOMER,
        ).first()

        if component is None:
            continue

        checked_orders += 1
        required_quantity = _to_decimal(component.quantity)

        selected_reservations, remaining_quantity = _select_units_from_pool(
            units=available_units,
            required_quantity=required_quantity,
            allow_larger_splittable_unit=component.inv_item.is_splittable,
        )

        if remaining_quantity == ZERO:
            used_unit_ids = {
                row["warehouse_unit"].id
                for row in selected_reservations
            }

            available_units = [
                unit
                for unit in available_units
                if unit.id not in used_unit_ids
            ]

            updated = SalesOrderIssue.objects.filter(
                sales_order=sales_order,
                stage=SalesOrderIssue.Stage.CONFIRMATION,
                issue_type=SalesOrderIssue.IssueType.CUSTOMER_COMPONENT_MISSING,
                related_component=component,
                status=SalesOrderIssue.Status.OPEN,
            ).update(
                status=SalesOrderIssue.Status.RESOLVED,
                resolved_at=now,
                last_checked_at=now,
            )

            resolved_issues += updated
            continue

        SalesOrderIssue.objects.update_or_create(
            sales_order=sales_order,
            stage=SalesOrderIssue.Stage.CONFIRMATION,
            issue_type=SalesOrderIssue.IssueType.CUSTOMER_COMPONENT_MISSING,
            related_component=component,
            defaults={
                "status": SalesOrderIssue.Status.OPEN,
                "severity": SalesOrderIssue.Severity.CRITICAL,
                "message": (
                    f"Не вистачає товару замовника: "
                    f"{component.inv_item.internal_code} — {component.inv_item.name}"
                ),
                "related_inv_item": component.inv_item,
                "missing_quantity": remaining_quantity,
                "last_checked_at": now,
                "resolved_at": None,
            },
        )

        opened_issues += 1

    return {
        "organization_id": organization_id,
        "inv_item_id": inv_item_id,
        "checked_orders": checked_orders,
        "resolved_issues": resolved_issues,
        "opened_issues": opened_issues,
    }