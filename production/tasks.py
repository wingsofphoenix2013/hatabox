import logging

from celery import shared_task

from production.models import (
    ProductionOrder,
    ProductionOrderMaterialSnapshot,
)
from production.services.material_snapshot import (
    build_production_order_material_snapshot,
)


logger = logging.getLogger(__name__)


@shared_task
def build_production_order_material_snapshot_task(
    *,
    production_order_id,
):
    logger.info(
        "ProductionOrder material snapshot started: production_order_id=%s",
        production_order_id,
    )

    snapshot, _ = ProductionOrderMaterialSnapshot.objects.get_or_create(
        production_order_id=production_order_id,
        defaults={
            "status": ProductionOrderMaterialSnapshot.Status.PROCESSING,
        },
    )

    snapshot.status = (
        ProductionOrderMaterialSnapshot.Status.PROCESSING
    )
    snapshot.error_message = ""

    snapshot.save(
        update_fields=[
            "status",
            "error_message",
            "updated_at",
        ]
    )

    try:
        production_order = ProductionOrder.objects.get(
            pk=production_order_id,
        )

        snapshot = build_production_order_material_snapshot(
            production_order=production_order,
        )

    except Exception as exc:
        logger.exception(
            "ProductionOrder material snapshot failed: production_order_id=%s",
            production_order_id,
        )

        if snapshot is not None:
            snapshot.status = (
                ProductionOrderMaterialSnapshot.Status.FAILED
            )
            snapshot.error_message = str(exc)

            snapshot.save(
                update_fields=[
                    "status",
                    "error_message",
                    "updated_at",
                ]
            )

        raise

    logger.info(
        "ProductionOrder material snapshot finished: production_order_id=%s snapshot_id=%s items=%s",
        production_order_id,
        snapshot.id,
        snapshot.items.count(),
    )

    return {
        "snapshot_id": snapshot.id,
        "items_count": snapshot.items.count(),
    }