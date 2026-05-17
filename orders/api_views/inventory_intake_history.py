from django.db import models
from django.db.models import Max

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from orders.models import (
    ExternalOrder,
    ExternalOrderItem,
    TollingOrder,
    TollingOrderItem,
)

from orders.serializers import InventoryIntakeHistoryItemSerializer


class InventoryIntakeHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        inv_item_id = request.query_params.get("inv_item")

        if not inv_item_id:
            return Response([])

        results = []

        external_items = (
            ExternalOrderItem.objects.filter(
                order__status=ExternalOrder.StatusChoices.COMPLETED,
                vendor_item__item_id=inv_item_id,
            )
            .select_related(
                "order",
                "order__vendor",
                "vendor_item",
                "vendor_item__item",
                "vendor_item__item__unit",
            )
            .annotate(
                actual_delivery_date=Max(
                    "receipt_items__receipt_document__receipt_date",
                    filter=models.Q(
                        receipt_items__receipt_document__completed=True,
                    ),
                )
            )
        )

        for item in external_items:
            results.append({
                "source_type": "external",

                "supplier_id": item.order.vendor_id,
                "supplier_name": item.order.vendor.name,

                "order_id": item.order_id,
                "order_no": item.order.order_no,
                "order_created_at": item.order.created_at,

                "order_item_id": item.id,

                "quantity": item.quantity,

                "unit_id": item.vendor_item.item.unit_id,
                "unit_name": item.vendor_item.item.unit.name,
                "unit_symbol": item.vendor_item.item.unit.symbol,

                "requires_unit_conversion": item.requires_unit_conversion,

                "agreed_price": item.agreed_price,

                "actual_delivery_date": item.actual_delivery_date,
            })

        tolling_items = (
            TollingOrderItem.objects.filter(
                order__status=TollingOrder.StatusChoices.COMPLETED,
                inv_item_id=inv_item_id,
            )
            .select_related(
                "order",
                "order__organization",
                "inv_item",
                "inv_item__unit",
            )
            .annotate(
                actual_delivery_date=Max(
                    "receipt_items__receipt_document__receipt_date",
                    filter=models.Q(
                        receipt_items__receipt_document__completed=True,
                    ),
                )
            )
        )

        for item in tolling_items:
            results.append({
                "source_type": "tolling",

                "supplier_id": item.order.organization_id,
                "supplier_name": item.order.organization.name,

                "order_id": item.order_id,
                "order_no": item.order.order_no,
                "order_created_at": item.order.created_at,

                "order_item_id": item.id,

                "quantity": item.quantity,

                "unit_id": item.inv_item.unit_id,
                "unit_name": item.inv_item.unit.name,
                "unit_symbol": item.inv_item.unit.symbol,

                "requires_unit_conversion": item.requires_unit_conversion,

                "agreed_price": None,

                "actual_delivery_date": item.actual_delivery_date,
            })

        results.sort(
            key=lambda x: (
                x["actual_delivery_date"] or x["order_created_at"].date(),
                x["order_created_at"],
            ),
            reverse=True,
        )

        serializer = InventoryIntakeHistoryItemSerializer(results, many=True)

        return Response(serializer.data)