from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from warehouse.models import MovementPlan
from warehouse.serializers import (
    MovementPlanSerializer,
    CreateMovementPlanSerializer,
    AddItemsToMovementPlanSerializer,
)
from warehouse.services.movement_plan import (
    create_movement_plan,
    add_items_to_plan,
    execute_movement_plan,
    cancel_movement_plan,
)


class MovementPlanViewSet(ModelViewSet):
    queryset = MovementPlan.objects.select_related(
        "target_location",
        "target_storage_place",
        "created_by",
    ).prefetch_related(
        "items",
        "items__warehouse_unit",
        "items__warehouse_unit__inventory_item",
    ).order_by("-created_at", "-id")

    serializer_class = MovementPlanSerializer
    permission_classes = [DjangoModelPermissions]

    def create(self, request, *args, **kwargs):
        serializer = CreateMovementPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = create_movement_plan(
            target_location=serializer.validated_data.get("target_location"),
            target_storage_place=serializer.validated_data.get("target_storage_place"),
            planned_at=serializer.validated_data.get("planned_at"),
            created_by=request.user if request.user.is_authenticated else None,
        )

        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"], url_path="add-items")
    def add_items(self, request, pk=None):
        plan = self.get_object()

        serializer = AddItemsToMovementPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        add_items_to_plan(
            plan=plan,
            inventory_item=serializer.validated_data["inventory_item"],
            quantity=serializer.validated_data["quantity"],
        )

        plan.refresh_from_db()

        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"], url_path="execute")
    def execute(self, request, pk=None):
        plan = self.get_object()

        execute_movement_plan(
            plan=plan,
            created_by=request.user if request.user.is_authenticated else None,
        )

        plan.refresh_from_db()

        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        plan = self.get_object()

        cancel_movement_plan(plan=plan)

        plan.refresh_from_db()

        return Response(self.get_serializer(plan).data)