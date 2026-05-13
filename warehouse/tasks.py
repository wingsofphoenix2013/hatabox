import logging

from celery import shared_task

from production.services.step_readiness_issues import (
    recalculate_production_step_readiness_issues,
)
from warehouse.services.shortage_recalculation import (
    recalculate_warehouse_shortages,
)


logger = logging.getLogger(__name__)


@shared_task
def recalculate_warehouse_shortages_task(
    *,
    inv_item_ids,
):
    logger.info(
        "Warehouse shortage recalculation started",
    )

    try:
        result = recalculate_warehouse_shortages(
            inv_item_ids=inv_item_ids,
        )

        readiness_result = recalculate_production_step_readiness_issues(
            inv_item_ids=inv_item_ids,
        )
    except Exception:
        logger.exception(
            "Warehouse shortage recalculation failed",
        )
        raise

    logger.info(
        (
            "Warehouse shortage recalculation finished: "
            "shortages=%s recalculated_at=%s "
            "checked_components=%s opened_issues=%s resolved_issues=%s"
        ),
        result["shortages"],
        result["recalculated_at"],
        readiness_result["checked_components"],
        readiness_result["opened_issues"],
        readiness_result["resolved_issues"],
    )

    return result