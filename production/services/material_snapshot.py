from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from production.models import (
    ProductionOrder,
    ProductionOrderMaterialSnapshot,
    ProductionOrderMaterialSnapshotItem,
)
from warehouse.models import (
    WarehouseProductionMovement,
    WarehouseProductionMovementItem,
    WarehouseUnit,
)


def build_production_order_material_snapshot(
    *,
    production_order,
):
    if production_order.status != ProductionOrder.Status.READY:
        raise ValidationError(
            "Snapshot можна створити лише для ready ProductionOrder."
        )

    movement_items = list(
        WarehouseProductionMovementItem.objects.select_related(
            "movement",
            "result_warehouse_unit",
            "result_warehouse_unit__inventory_item",
            "result_warehouse_unit__source_order_item",
            "result_warehouse_unit__source_receipt_item",
            "result_warehouse_unit__tolling_source_order_item",
            "result_warehouse_unit__tolling_source_receipt_item",
            "result_warehouse_unit__tolling_source_order_item__order",
        ).filter(
            movement__production_order=production_order,
            movement__status=WarehouseProductionMovement.Status.EXECUTED,
            result_warehouse_unit__status=WarehouseUnit.Status.CONSUMED,
        )
    )

    with transaction.atomic():
        snapshot, _ = (
            ProductionOrderMaterialSnapshot.objects
            .select_for_update()
            .get_or_create(
                production_order=production_order,
            )
        )

        snapshot.items.all().delete()

        items_to_create = []

        for movement_item in movement_items:
            unit = movement_item.result_warehouse_unit

            if unit.source_order_item_id:
                origin_type = (
                    ProductionOrderMaterialSnapshotItem.OriginType.OWN
                )

            elif unit.tolling_source_order_item_id:
                if (
                    unit.tolling_source_order_item.order.organization.type
                    == unit.tolling_source_order_item.order.organization.Type.CHARITY
                ):
                    origin_type = (
                        ProductionOrderMaterialSnapshotItem.OriginType.DONOR
                    )
                else:
                    origin_type = (
                        ProductionOrderMaterialSnapshotItem.OriginType.CUSTOMER
                    )
            else:
                continue

            external_order = None
            external_order_no = ""

            vendor = None
            vendor_name = ""

            vendor_item = None
            vendor_sku = ""

            if unit.source_order_item_id:
                external_order = unit.source_order_item.order
                external_order_no = external_order.order_no

                vendor = external_order.vendor
                vendor_name = vendor.name

                vendor_item = unit.source_order_item.vendor_item
                vendor_sku = vendor_item.vendor_sku

            items_to_create.append(
                ProductionOrderMaterialSnapshotItem(
                    snapshot=snapshot,
                    inv_item_id=unit.inventory_item_id,
                    warehouse_unit=unit,
                    quantity=movement_item.quantity,
                    origin_type=origin_type,
                    source_order_item_id=unit.source_order_item_id,
                    source_receipt_item_id=unit.source_receipt_item_id,
                    external_order=external_order,
                    external_order_no=external_order_no,
                    vendor=vendor,
                    vendor_name=vendor_name,
                    vendor_item=vendor_item,
                    vendor_sku=vendor_sku,
                    tolling_source_order_item_id=(
                        unit.tolling_source_order_item_id
                    ),
                    tolling_source_receipt_item_id=(
                        unit.tolling_source_receipt_item_id
                    ),
                )
            )

        if items_to_create:
            ProductionOrderMaterialSnapshotItem.objects.bulk_create(
                items_to_create,
            )

        snapshot.status = (
            ProductionOrderMaterialSnapshot.Status.COMPLETED
        )
        snapshot.error_message = ""
        snapshot.calculated_at = timezone.now()

        snapshot.save(
            update_fields=[
                "status",
                "error_message",
                "calculated_at",
                "updated_at",
            ]
        )

    return snapshot