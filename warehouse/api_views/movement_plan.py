from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.db.models import Count

from warehouse.models import MovementPlan
from warehouse.serializers import (
    MovementPlanSerializer,
    MovementPlanListSerializer,
    CreateMovementPlanSerializer,
    AddItemsToMovementPlanSerializer,
    UpdateMovementPlanSerializer,
    RemoveMovementPlanItemSerializer,
    ChangeMovementPlanItemQuantitySerializer,
    ChangeMovementPlanInventoryItemQuantitySerializer,
    RemoveMovementPlanInventoryItemSerializer,
)
from warehouse.services.movement_plan import (
    create_movement_plan,
    update_movement_plan,
    add_items_to_plan,
    remove_item_from_plan,
    change_plan_item_quantity,
    change_inventory_item_quantity_in_plan,
    remove_inventory_item_from_plan,
    execute_movement_plan,
    cancel_movement_plan,
)
from warehouse.services.movement_plan_invoice import generate_and_save_movement_plan_invoice

class MovementPlanViewSet(ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    queryset = MovementPlan.objects.select_related(
        "target_location",
        "target_storage_place",
        "created_by",
    ).annotate(
        items_count=Count("items")
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
            comment=serializer.validated_data.get("comment", ""),
            created_by=request.user if request.user.is_authenticated else None,
        )

        return Response(self.get_serializer(plan).data)
        
    def partial_update(self, request, *args, **kwargs):
        plan = self.get_object()

        serializer = UpdateMovementPlanSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        destination_provided = (
            "target_location" in serializer.validated_data
            or "target_storage_place" in serializer.validated_data
        )

        plan = update_movement_plan(
            plan=plan,
            target_location=serializer.validated_data.get("target_location"),
            target_storage_place=serializer.validated_data.get("target_storage_place"),
            planned_at=serializer.validated_data.get("planned_at"),
            comment=serializer.validated_data.get("comment"),
            destination_provided=destination_provided,
        )

        plan = self.get_queryset().get(pk=plan.pk)

        return Response(self.get_serializer(plan).data)

    def get_queryset(self):
        queryset = self.queryset

        if self.action != "list":
            queryset = queryset.prefetch_related(
                "items",
                "items__warehouse_unit",
                "items__warehouse_unit__inventory_item",
                "items__warehouse_unit__inventory_item__unit",
                "items__warehouse_unit__location",
                "items__warehouse_unit__storage_place",
                "items__warehouse_unit__storage_place__location",
                "items__warehouse_unit__storage_place__parent",
                "items__warehouse_unit__storage_place__parent__parent",
                "items__warehouse_unit__storage_place__parent__parent__parent",
            )

        status_list = self.request.query_params.getlist("status")
        if status_list:
            queryset = queryset.filter(status__in=status_list)

        created_at_from = self.request.query_params.get("created_at_from")
        if created_at_from:
            queryset = queryset.filter(created_at__gte=created_at_from)

        created_at_to = self.request.query_params.get("created_at_to")
        if created_at_to:
            queryset = queryset.filter(created_at__lte=created_at_to)

        planned_at_from = self.request.query_params.get("planned_at_from")
        if planned_at_from:
            queryset = queryset.filter(planned_at__gte=planned_at_from)

        planned_at_to = self.request.query_params.get("planned_at_to")
        if planned_at_to:
            queryset = queryset.filter(planned_at__lte=planned_at_to)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return MovementPlanListSerializer
        return MovementPlanSerializer
        
    @action(detail=True, methods=["post"], url_path="change-inventory-item-quantity")
    def change_inventory_item_quantity(self, request, pk=None):
        plan = self.get_object()

        serializer = ChangeMovementPlanInventoryItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = change_inventory_item_quantity_in_plan(
            plan=plan,
            inventory_item=serializer.validated_data["inventory_item"],
            quantity=serializer.validated_data["quantity"],
        )

        plan = self.get_queryset().get(pk=plan.pk)

        return Response(self.get_serializer(plan).data)
        
    @action(detail=True, methods=["post"], url_path="remove-inventory-item")
    def remove_inventory_item(self, request, pk=None):
        plan = self.get_object()

        serializer = RemoveMovementPlanInventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = remove_inventory_item_from_plan(
            plan=plan,
            inventory_item=serializer.validated_data["inventory_item"],
        )

        return Response(result)

    @action(detail=True, methods=["post"], url_path="add-items")
    def add_items(self, request, pk=None):
        plan = self.get_object()

        serializer = AddItemsToMovementPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            add_items_to_plan(
                plan=plan,
                inventory_item=serializer.validated_data["inventory_item"],
                quantity=serializer.validated_data["quantity"],
            )
        except Exception as exc:
            import traceback
            print("ADD ITEMS ERROR")
            print(f"plan_id={plan.id}")
            print(f"inventory_item={serializer.validated_data.get('inventory_item')}")
            print(f"quantity={serializer.validated_data.get('quantity')}")
            print(traceback.format_exc())
            raise exc

        plan = self.get_queryset().get(pk=plan.pk)

        return Response(self.get_serializer(plan).data)
        
    @action(detail=True, methods=["post"], url_path="remove-item")
    def remove_item(self, request, pk=None):
        plan = self.get_object()

        serializer = RemoveMovementPlanItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = remove_item_from_plan(
            plan=plan,
            item_id=serializer.validated_data["item_id"],
        )

        return Response(result)
        
    @action(detail=True, methods=["post"], url_path="change-item-quantity")
    def change_item_quantity(self, request, pk=None):
        plan = self.get_object()

        serializer = ChangeMovementPlanItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = change_plan_item_quantity(
            plan=plan,
            item_id=serializer.validated_data["item_id"],
            quantity=serializer.validated_data["quantity"],
        )

        plan = self.get_queryset().get(pk=plan.pk)

        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"], url_path="generate-invoice")
    def generate_invoice(self, request, pk=None):
        plan = self.get_object()

        if plan.status != MovementPlan.Status.ACTIVE:
            raise ValidationError("Накладну можна сформувати лише для active плану.")

        plan = generate_and_save_movement_plan_invoice(plan)

        plan = self.get_queryset().get(pk=plan.pk)

        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"], url_path="execute")
    def execute(self, request, pk=None):
        plan = self.get_object()

        execute_movement_plan(
            plan=plan,
            created_by=request.user if request.user.is_authenticated else None,
        )

        plan = self.get_queryset().get(pk=plan.pk)

        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        plan = self.get_object()

        cancel_movement_plan(plan=plan)

        plan = self.get_queryset().get(pk=plan.pk)

        return Response(self.get_serializer(plan).data)