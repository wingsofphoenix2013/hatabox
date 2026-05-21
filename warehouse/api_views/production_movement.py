from django.db.models import Count, Q

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from warehouse.models import WarehouseProductionMovement
from warehouse.serializers import (
    UpdateWarehouseProductionMovementCommentSerializer,
    WarehouseProductionMovementListSerializer,
    WarehouseProductionMovementSerializer,
)
from warehouse.services.production_movement import (
    cancel_production_movement,
    execute_production_movement,
)
from sales.models import SalesOrderEvent
from sales.services.events import create_sales_order_event
from warehouse.services.production_movement_invoice import (
    generate_and_save_production_movement_invoice,
)


class WarehouseProductionMovementViewSet(ModelViewSet):
    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    permission_classes = [DjangoModelPermissions]

    queryset = WarehouseProductionMovement.objects.select_related(
        "production_order",
        "production_order__sales_order",
        "production_order_step",
        "created_by",
    ).annotate(
        items_count=Count("items"),
    ).order_by(
        "-created_at",
        "-id",
    )

    serializer_class = WarehouseProductionMovementSerializer

    def get_queryset(self):
        queryset = self.queryset

        if self.action != "list":
            queryset = queryset.prefetch_related(
                "items",
                "items__production_reservation",
                "items__source_warehouse_unit",
                "items__result_warehouse_unit",
                "items__inventory_item",
                "items__inventory_item__unit",
                "items__executed_source_location",
                "items__executed_source_storage_place",
            )

        production_order = self.request.query_params.get(
            "production_order"
        )
        if production_order:
            queryset = queryset.filter(
                production_order_id=production_order,
            )

        production_order_step = self.request.query_params.get(
            "production_order_step"
        )
        if production_order_step:
            queryset = queryset.filter(
                production_order_step_id=production_order_step,
            )

        production_order_step_name = self.request.query_params.get(
            "production_order_step_name"
        )
        if production_order_step_name:
            queryset = queryset.filter(
                production_order_step__name__icontains=(
                    production_order_step_name
                ),
            )

        sales_order = self.request.query_params.get(
            "sales_order"
        )
        if sales_order:
            queryset = queryset.filter(
                production_order__sales_order_id=sales_order,
            )

        production_order_serial_number = (
            self.request.query_params.get(
                "production_order_serial_number"
            )
        )

        if production_order_serial_number:
            queryset = queryset.filter(
                production_order__serial_number__icontains=(
                    production_order_serial_number
                ),
            )

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(
            self.get_queryset()
        )

        summary = queryset.aggregate(
            created_count=Count(
                "id",
                filter=Q(
                    status=WarehouseProductionMovement.Status.CREATED,
                ),
            ),
            executed_count=Count(
                "id",
                filter=Q(
                    status=WarehouseProductionMovement.Status.EXECUTED,
                ),
            ),
            cancelled_count=Count(
                "id",
                filter=Q(
                    status=WarehouseProductionMovement.Status.CANCELLED,
                ),
            ),
        )

        summary["has_created"] = (
            summary["created_count"] > 0
        )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
            )

            response = self.get_paginated_response(
                serializer.data,
            )

            response.data["summary"] = summary

            return response

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response({
            "summary": summary,
            "results": serializer.data,
        })

    def get_serializer_class(self):
        if self.action == "list":
            return WarehouseProductionMovementListSerializer

        return WarehouseProductionMovementSerializer

    @action(detail=True, methods=["post"], url_path="update-comment")
    def update_comment(self, request, pk=None):
        movement = self.get_object()

        if movement.status != WarehouseProductionMovement.Status.CREATED:
            raise ValidationError(
                "Коментар можна змінювати лише для created документа."
            )

        serializer = UpdateWarehouseProductionMovementCommentSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        movement.comment = serializer.validated_data["comment"]
        movement.save(update_fields=["comment"])

        movement = self.get_queryset().get(pk=movement.pk)

        return Response(
            self.get_serializer(movement).data
        )

    @action(detail=True, methods=["post"], url_path="execute")
    def execute(self, request, pk=None):
        movement = self.get_object()

        movement = execute_production_movement(
            movement=movement,
            created_by=request.user if request.user.is_authenticated else None,
        )

        movement = self.get_queryset().get(pk=movement.pk)

        return Response(
            self.get_serializer(movement).data
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        movement = self.get_object()

        movement = cancel_production_movement(
            movement=movement,
        )

        movement = self.get_queryset().get(pk=movement.pk)

        return Response(
            self.get_serializer(movement).data
        )

    @action(detail=True, methods=["post"], url_path="generate-invoice")
    def generate_invoice(self, request, pk=None):
        movement = self.get_object()

        if movement.status != WarehouseProductionMovement.Status.CREATED:
            raise ValidationError(
                "Накладну можна сформувати лише для created документа."
            )

        movement = generate_and_save_production_movement_invoice(
            movement,
        )

        create_sales_order_event(
            sales_order=movement.production_order.sales_order,
            event_type=SalesOrderEvent.EventType.PRODUCTION_MOVEMENT_INVOICE_GENERATED,
            source=SalesOrderEvent.Source.WAREHOUSE,
            title="Сформовано накладну видачі у виробництво",
            message=(
                f"Сформовано накладну для етапу "
                f"{movement.production_order_step.sequence_number}: "
                f"{movement.production_order_step.name}."
            ),
            payload={
                "production_movement_id": movement.id,
                "production_order_id": movement.production_order_id,
                "production_order_step_id": (
                    movement.production_order_step_id
                ),
            },
            created_by=request.user,
        )

        movement = self.get_queryset().get(pk=movement.pk)

        return Response(
            self.get_serializer(movement).data
        )