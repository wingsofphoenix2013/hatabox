from collections import defaultdict

from production.models import ProductionOrder, ProductionOrderStep
from sales.models import SalesOrderIssue
from warehouse.models import WarehouseProductionMovement


def build_sales_order_production_readiness(
    *,
    sales_order,
):
    try:
        production_order = sales_order.production_order
    except ProductionOrder.DoesNotExist:
        return {
            "sales_order": sales_order.id,
            "production_order": None,
            "production_order_status": None,
            "can_edit_production_diary": False,
            "readiness_status": "pending",
            "is_ready": False,
            "message": "Виробничі етапи ще формуються.",
            "summary": None,
            "steps": [],
        }

    steps = list(
        production_order.steps.order_by(
            "sequence_number",
            "id",
        )
    )

    step_ids = [
        step.id
        for step in steps
    ]

    movements = list(
        WarehouseProductionMovement.objects.filter(
            production_order=production_order,
        ).order_by(
            "production_order_step_id",
            "-created_at",
            "-id",
        )
    )

    movement_by_step_id = {}

    for movement in movements:
        if movement.production_order_step_id not in movement_by_step_id:
            movement_by_step_id[
                movement.production_order_step_id
            ] = movement

    open_issues = list(
        SalesOrderIssue.objects.select_related(
            "related_inv_item",
            "related_inv_item__unit",
            "production_order_step",
            "production_order_step_component",
        ).filter(
            sales_order=sales_order,
            production_order=production_order,
            production_order_step_id__in=step_ids,
            stage=SalesOrderIssue.Stage.PRODUCTION_STEP_CONFIRMATION,
            issue_type=SalesOrderIssue.IssueType.STEP_COMPONENT_MISSING,
            status=SalesOrderIssue.Status.OPEN,
        ).order_by(
            "production_order_step__sequence_number",
            "severity",
            "id",
        )
    )

    issues_by_step_id = defaultdict(list)

    for issue in open_issues:
        issues_by_step_id[issue.production_order_step_id].append(issue)

    steps_payload = []

    total_open_critical_issues_count = 0
    total_open_non_critical_issues_count = 0

    previous_step_payload = None

    for step in steps:
        step_issues = issues_by_step_id.get(step.id, [])

        open_critical_issues_count = sum(
            1
            for issue in step_issues
            if issue.severity == SalesOrderIssue.Severity.CRITICAL
        )
        open_non_critical_issues_count = sum(
            1
            for issue in step_issues
            if issue.severity == SalesOrderIssue.Severity.NON_CRITICAL
        )

        total_open_critical_issues_count += open_critical_issues_count
        total_open_non_critical_issues_count += open_non_critical_issues_count

        movement = movement_by_step_id.get(step.id)

        production_movement_components_transferred = (
            movement.status == WarehouseProductionMovement.Status.EXECUTED
            if movement
            else False
        )

        production_step_can_start = (
            step.status == ProductionOrderStep.Status.CONFIRMED
            and production_movement_components_transferred
            and (
                previous_step_payload is None
                or previous_step_payload["status"]
                == ProductionOrderStep.Status.FINISHED
            )
        )

        steps_payload.append({
            "production_order_step": step.id,
            "sequence_number": step.sequence_number,
            "name": step.name,
            "status": step.status,
            "production_movement": (
                movement.id
                if movement
                else None
            ),
            "production_movement_status": (
                movement.status
                if movement
                else None
            ),
            "production_movement_invoice_file": (
                movement.invoice_file.url
                if movement and movement.invoice_file
                else None
            ),
            "production_movement_invoice_generated_at": (
                movement.invoice_generated_at
                if movement
                else None
            ),
            "production_movement_components_transferred": (
                production_movement_components_transferred
            ),
            "production_step_can_start": production_step_can_start,
            "can_be_confirmed": (
                step.status == ProductionOrderStep.Status.DRAFT
                and open_critical_issues_count == 0
            ),
            "open_critical_issues_count": open_critical_issues_count,
            "open_non_critical_issues_count": open_non_critical_issues_count,
            "issues": [
                {
                    "issue": issue.id,
                    "severity": issue.severity,
                    "inv_item": issue.related_inv_item_id,
                    "inv_item_code": (
                        issue.related_inv_item.internal_code
                        if issue.related_inv_item
                        else None
                    ),
                    "inv_item_name": (
                        issue.related_inv_item.name
                        if issue.related_inv_item
                        else None
                    ),
                    "missing_quantity": issue.missing_quantity,
                    "unit_symbol": (
                        issue.related_inv_item.unit.symbol
                        if issue.related_inv_item
                        else None
                    ),
                    "is_required_for_step_start": (
                        issue.production_order_step_component.is_required_for_step_start
                        if issue.production_order_step_component
                        else None
                    ),
                    "message": issue.message,
                    "last_checked_at": issue.last_checked_at,
                }
                for issue in step_issues
            ],
        })

        previous_step_payload = steps_payload[-1]

    next_step_payload = next(
        (
            step
            for step in steps_payload
            if step["status"] == ProductionOrderStep.Status.DRAFT
        ),
        None,
    )

    first_step_payload = next(
        (
            step
            for step in steps_payload
            if step["sequence_number"] == 1
        ),
        None,
    )

    return {
        "sales_order": sales_order.id,
        "production_order": production_order.id,
        "production_order_status": production_order.status,
        "can_edit_production_diary": production_order.status not in [
            ProductionOrder.Status.READY,
            ProductionOrder.Status.CANCELLED,
        ],
        "readiness_status": "ready",
        "is_ready": True,
        "message": None,
        "summary": {
            "next_step": (
                next_step_payload["production_order_step"]
                if next_step_payload
                else None
            ),
            "next_step_name": (
                next_step_payload["name"]
                if next_step_payload
                else None
            ),
            "can_confirm_next_step": (
                next_step_payload["can_be_confirmed"]
                if next_step_payload
                else False
            ),
            "production_order_can_start": (
                production_order.status == ProductionOrder.Status.DRAFT
                and first_step_payload is not None
                and first_step_payload["status"] == ProductionOrderStep.Status.CONFIRMED
            ),
            "open_critical_issues_count": total_open_critical_issues_count,
            "open_non_critical_issues_count": total_open_non_critical_issues_count,
        },
        "steps": steps_payload,
    }