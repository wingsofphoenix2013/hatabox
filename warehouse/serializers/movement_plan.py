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


class MovementPlanListSerializer(serializers.ModelSerializer):
    target_location_code = serializers.SerializerMethodField()
    target_location_name = serializers.SerializerMethodField()
    target_storage_place_code = serializers.CharField(source="target_storage_place.code", read_only=True)
    target_storage_place_display_name = serializers.CharField(source="target_storage_place.get_display_name", read_only=True)
    target_storage_place_full_display = serializers.CharField(source="target_storage_place.get_display_name_verbose", read_only=True)
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MovementPlan
        fields = [
            "id",
            "status",
            "target_location",
            "target_location_code",
            "target_location_name",
            "target_storage_place",
            "target_storage_place_code",
            "target_storage_place_display_name",
            "target_storage_place_full_display",
            "created_by",
            "planned_at",
            "comment",
            "created_at",
            "items_count",
        ]
        
    def get_target_location_code(self, obj):
        if obj.target_location is not None:
            return obj.target_location.code
        if obj.target_storage_place is not None:
            return obj.target_storage_place.location.code
        return None

    def get_target_location_name(self, obj):
        if obj.target_location is not None:
            return obj.target_location.name
        if obj.target_storage_place is not None:
            return obj.target_storage_place.location.name
        return None


class MovementPlanSerializer(serializers.ModelSerializer):
    items = MovementPlanItemSerializer(many=True, read_only=True)
    target_location_code = serializers.SerializerMethodField()
    target_location_name = serializers.SerializerMethodField()
    target_storage_place_code = serializers.CharField(source="target_storage_place.code", read_only=True)
    target_storage_place_display_name = serializers.CharField(source="target_storage_place.get_display_name", read_only=True)
    target_storage_place_full_display = serializers.CharField(source="target_storage_place.get_display_name_verbose", read_only=True)
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MovementPlan
        fields = [
            "id",
            "status",
            "target_location",
            "target_location_code",
            "target_location_name",
            "target_storage_place",
            "target_storage_place_code",
            "target_storage_place_display_name",
            "target_storage_place_full_display",
            "created_by",
            "planned_at",
            "comment",
            "created_at",
            "items_count",
            "items",
        ]
        read_only_fields = [
            "status",
            "created_by",
            "created_at",
            "items",
        ]

    def get_target_location_code(self, obj):
        if obj.target_location is not None:
            return obj.target_location.code
        if obj.target_storage_place is not None:
            return obj.target_storage_place.location.code
        return None

    def get_target_location_name(self, obj):
        if obj.target_location is not None:
            return obj.target_location.name
        if obj.target_storage_place is not None:
            return obj.target_storage_place.location.name
        return None

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
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
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