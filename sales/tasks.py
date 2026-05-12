import logging

from celery import shared_task

from sales.services.issues import (
    recalculate_customer_component_confirmation_issues,
)


logger = logging.getLogger(__name__)


@shared_task
def recalculate_customer_component_confirmation_issues_task(
    *,
    organization_id,
    inv_item_id,
):
    logger.info(
        "SalesOrderIssue recalculation started: organization_id=%s inv_item_id=%s",
        organization_id,
        inv_item_id,
    )

    try:
        result = recalculate_customer_component_confirmation_issues(
            organization_id=organization_id,
            inv_item_id=inv_item_id,
        )
    except Exception:
        logger.exception(
            "SalesOrderIssue recalculation failed: organization_id=%s inv_item_id=%s",
            organization_id,
            inv_item_id,
        )
        raise

    logger.info(
        "SalesOrderIssue recalculation finished: organization_id=%s inv_item_id=%s checked_orders=%s resolved_issues=%s opened_issues=%s",
        organization_id,
        inv_item_id,
        result["checked_orders"],
        result["resolved_issues"],
        result["opened_issues"],
    )

    return result