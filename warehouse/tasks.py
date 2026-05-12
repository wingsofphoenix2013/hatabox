import logging

from celery import shared_task

from warehouse.services.shortage_recalculation import (
    recalculate_warehouse_shortages,
)


logger = logging.getLogger(__name__)


@shared_task
def recalculate_warehouse_shortages_task():
    logger.info(
        "Warehouse shortage recalculation started",
    )

    try:
        result = recalculate_warehouse_shortages()
    except Exception:
        logger.exception(
            "Warehouse shortage recalculation failed",
        )
        raise

    logger.info(
        "Warehouse shortage recalculation finished: shortages=%s recalculated_at=%s",
        result["shortages"],
        result["recalculated_at"],
    )

    return result