from rest_framework import serializers

from inventory.models import InvItem
from warehouse.models import (
    MovementPlan,
    MovementPlanItem,
    WarehouseLocation,
    WarehouseStoragePlace,
)


class MovementPlanItemSerializer(serializers.ModelSerializer):
    warehouse_unit_id = serializers.IntegerField(source="warehouse_unit.id", read_only=True)
    inventory_item_id = serializers.IntegerField(source="warehouse_unit.inventory_item_id", read_only=True)
    inventory_item_name = serializers.CharField(source="warehouse_unit.inventory_item.name", read_only=True)

    class Meta:
        model = MovementPlanItem
        fields = [
            "id",
            "warehouse_unit_id",
            "inventory_item_id",
            "inventory_item_name",
            "reserved_quantity",
            "move_quantity",
            "remainder_quantity",
            "requires_split",
        ]


class MovementPlanSerializer(serializers.ModelSerializer):
    items = MovementPlanItemSerializer(many=True, read_only=True)

    class Meta:
        model = MovementPlan
        fields = [
            "id",
            "status",
            "target_location",
            "target_storage_place",
            "created_by",
            "planned_at",
            "created_at",
            "items",
        ]
        read_only_fields = [
            "status",
            "created_by",
            "created_at",
            "items",
        ]


class CreateMovementPlanSerializer(serializers.Serializer):
    target_location = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseLocation.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    target_storage_place = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseStoragePlace.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    planned_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        target_location = attrs.get("target_location")
        target_storage_place = attrs.get("target_storage_place")

        if (target_location is None) == (target_storage_place is None):
            raise serializers.ValidationError(
                "Потрібно вказати або target_location, або target_storage_place, але не обидва одночасно."
            )

        return attrs


class AddItemsToMovementPlanSerializer(serializers.Serializer):
    inventory_item = serializers.PrimaryKeyRelatedField(
        queryset=InvItem.objects.filter(is_active=True)
    )
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )