from django.db.models import Count

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
from warehouse.services.production_movement_invoice import (
    generate_and_save_production_movement_invoice,
)


class WarehouseProductionMovementViewSet(ModelViewSet):
    http_method_names = [
        "get",
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

        sales_order = self.request.query_params.get(
            "sales_order"
        )
        if sales_order:
            queryset = queryset.filter(
                production_order__sales_order_id=sales_order,
            )

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        return queryset

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

        movement = self.get_queryset().get(pk=movement.pk)

        return Response(
            self.get_serializer(movement).data
        )