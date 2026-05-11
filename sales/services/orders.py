from decimal import Decimal

from django.db import transaction

from inventory.models import ProductStepItem
from sales.models import SalesOrder, SalesOrderComponent, SalesOrderIssue


def create_sales_order_components(sales_order):
    if sales_order.components.exists():
        return

    step_items = ProductStepItem.objects.select_related(
        "inv_item",
    ).filter(
        product_step__product_id=sales_order.product_id,
    )

    components_by_inv_item = {}

    for step_item in step_items:
        inv_item_id = step_item.inv_item_id

        if inv_item_id not in components_by_inv_item:
            components_by_inv_item[inv_item_id] = {
                "inv_item": step_item.inv_item,
                "quantity": Decimal("0.000"),
            }

        components_by_inv_item[inv_item_id]["quantity"] += step_item.quantity

    components_to_create = []

    for component_data in components_by_inv_item.values():
        components_to_create.append(
            SalesOrderComponent(
                sales_order=sales_order,
                inv_item=component_data["inv_item"],
                quantity=component_data["quantity"],
                fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
                is_required_for_start=component_data["inv_item"].is_required_for_production_start,
            )
        )

    for component in components_to_create:
        component.full_clean()

    SalesOrderComponent.objects.bulk_create(components_to_create)


def create_sales_order(
    *,
    organization,
    product,
    created_by,
    customer_responsible_person=None,
    comment="",
):
    with transaction.atomic():
        sales_order = SalesOrder.objects.create(
            organization=organization,
            product=product,
            created_by=created_by,
            customer_responsible_person=customer_responsible_person,
            comment=comment,
        )

        create_sales_order_components(sales_order)

    return sales_order


def check_sales_order_can_confirm(sales_order):
    customer_components = list(
        sales_order.components.select_related(
            "inv_item",
        ).filter(
            fulfillment_mode=SalesOrderComponent.FulfillmentMode.CUSTOMER,
        )
    )

    if not customer_components:
        return {
            "can_confirm": True,
            "missing_components": [],
        }

    from warehouse.services.production_reservation import (
        _build_available_unit_pools,
        _select_units_from_pool,
        _to_decimal,
    )

    item_ids = [
        component.inv_item_id
        for component in customer_components
    ]

    available_unit_pools = _build_available_unit_pools(
        sales_order=sales_order,
        item_ids=item_ids,
    )

    missing_components = []
    missing_component_ids = set()

    for component in customer_components:
        required_quantity = _to_decimal(component.quantity)

        selected_reservations, remaining_quantity = _select_units_from_pool(
            units=available_unit_pools[component.inv_item_id]["customer"],
            required_quantity=required_quantity,
            allow_larger_splittable_unit=component.inv_item.is_splittable,
        )

        reserved_quantity = required_quantity - remaining_quantity

        if remaining_quantity > Decimal("0.000"):
            missing_component_ids.add(component.id)

            missing_components.append({
                "component_id": component.id,
                "inv_item": component.inv_item_id,
                "inv_item_code": component.inv_item.internal_code,
                "inv_item_name": component.inv_item.name,
                "required_quantity": required_quantity,
                "available_quantity": reserved_quantity,
                "missing_quantity": remaining_quantity,
            })

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
                    "last_checked_at": timezone.now(),
                    "resolved_at": None,
                },
            )

    resolved_now = timezone.now()

    open_confirmation_issues = SalesOrderIssue.objects.filter(
        sales_order=sales_order,
        stage=SalesOrderIssue.Stage.CONFIRMATION,
        issue_type=SalesOrderIssue.IssueType.CUSTOMER_COMPONENT_MISSING,
        status=SalesOrderIssue.Status.OPEN,
    ).exclude(
        related_component_id__in=missing_component_ids,
    )

    for issue in open_confirmation_issues:
        issue.status = SalesOrderIssue.Status.RESOLVED
        issue.resolved_at = resolved_now
        issue.last_checked_at = resolved_now

    if open_confirmation_issues:
        SalesOrderIssue.objects.bulk_update(
            open_confirmation_issues,
            ["status", "resolved_at", "last_checked_at"],
        )

    return {
        "can_confirm": len(missing_components) == 0,
        "missing_components": missing_components,
    }