from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from production.models import ProductionOrderStep
from warehouse.models import WarehouseProductionReservation
from warehouse.serializers import (
    WarehouseProductionReservationListSerializer,
)


class WarehouseProductionReservationViewSet(ReadOnlyModelViewSet):
    pagination_class = None

    def _get_base_queryset(self):
        queryset = self.queryset

        inv_item = self.request.query_params.get("inv_item")
        if inv_item:
            queryset = queryset.filter(
                sales_order_component__inv_item_id=inv_item,
            )

        return queryset

    def list(self, request, *args, **kwargs):
        rows = []

        for row in self.get_queryset():
            rows.append({
                "serial_number": (
                    row["sales_order__production_order__serial_number"]
                ),

                "inv_item": row[
                    "sales_order_component__inv_item_id"
                ],
                "inv_item_code": row[
                    "sales_order_component__inv_item__internal_code"
                ],
                "inv_item_name": row[
                    "sales_order_component__inv_item__name"
                ],
                "unit_symbol": row[
                    "sales_order_component__inv_item__unit__symbol"
                ],

                "organization": row["sales_order__organization_id"],
                "organization_name": row[
                    "sales_order__organization__name"
                ],

                "product_name": row[
                    "sales_order__product__product_family__name"
                ],
                "product_code": row[
                    "sales_order__product__code"
                ],

                "source_product_step": row[
                    "production_order_step_component__production_order_step__source_product_step_id"
                ],
                "source_product_step_name": row[
                    "production_order_step_component__production_order_step__source_product_step__name"
                ],

                "production_order_step": row[
                    "production_order_step_component__production_order_step_id"
                ],
                "production_order_step_status": row[
                    "production_order_step_component__production_order_step__status"
                ],
                "production_order_step_status_display": (
                    ProductionOrderStep.Status(
                        row[
                            "production_order_step_component__production_order_step__status"
                        ]
                    ).label
                    if row[
                        "production_order_step_component__production_order_step__status"
                    ]
                    else None
                ),

                "quantity": row["quantity"],
                "reservation_status": row["status"],

                "sales_order": row["sales_order_id"],
                "production_order": row[
                    "production_order_step_component__production_order_step__production_order_id"
                ],
            })

        serializer = self.get_serializer(
            rows,
            many=True,
        )

        return Response(serializer.data)
    permission_classes = [DjangoModelPermissions]
    serializer_class = WarehouseProductionReservationListSerializer

    queryset = WarehouseProductionReservation.objects.select_related(
        "sales_order",
        "sales_order__organization",
        "sales_order__product",
        "sales_order__product__product_family",
        "sales_order__production_order",
        "sales_order_component",
        "sales_order_component__inv_item",
        "sales_order_component__inv_item__unit",
        "production_order_step_component",
        "production_order_step_component__production_order_step",
        "production_order_step_component__production_order_step__source_product_step",
    )

    def get_queryset(self):
        queryset = self._get_base_queryset()

        return queryset.values(
            "sales_order__production_order__serial_number",

            "sales_order_component__inv_item_id",
            "sales_order_component__inv_item__internal_code",
            "sales_order_component__inv_item__name",
            "sales_order_component__inv_item__unit__symbol",

            "sales_order__organization_id",
            "sales_order__organization__name",

            "sales_order__product__product_family__name",
            "sales_order__product__code",

            "production_order_step_component__production_order_step__source_product_step_id",
            "production_order_step_component__production_order_step__source_product_step__name",

            "production_order_step_component__production_order_step_id",
            "production_order_step_component__production_order_step__status",

            "status",

            "sales_order_id",

            "production_order_step_component__production_order_step__production_order_id",
        ).annotate(
            quantity=Sum("quantity"),
        ).order_by(
            "-sales_order__production_order__serial_number",
            "-sales_order_id",
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        queryset = self._get_base_queryset()

        total_quantity = queryset.aggregate(
            total_quantity=Coalesce(
                Sum("quantity"),
                Decimal("0.000"),
            )
        )["total_quantity"]

        by_reservation_status = []

        for row in queryset.values(
            "status",
        ).annotate(
            quantity=Sum("quantity"),
        ).order_by(
            "status",
        ):
            by_reservation_status.append({
                "status": row["status"],
                "status_display": (
                    WarehouseProductionReservation.Status(
                        row["status"]
                    ).label
                ),
                "quantity": row["quantity"],
            })

        by_production_order_step_status = []

        for row in queryset.values(
            "production_order_step_component__production_order_step__status",
        ).annotate(
            quantity=Sum("quantity"),
        ).order_by(
            "production_order_step_component__production_order_step__status",
        ):
            step_status = row[
                "production_order_step_component__production_order_step__status"
            ]

            by_production_order_step_status.append({
                "status": step_status,
                "status_display": (
                    ProductionOrderStep.Status(step_status).label
                    if step_status
                    else None
                ),
                "quantity": row["quantity"],
            })

        return Response({
            "total_quantity": total_quantity,
            "by_reservation_status": by_reservation_status,
            "by_production_order_step_status": (
                by_production_order_step_status
            ),
        })