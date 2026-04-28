from django.utils import timezone

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
    source_location_code = serializers.SerializerMethodField()
    source_location_name = serializers.SerializerMethodField()
    source_storage_place_display_name = serializers.SerializerMethodField()
    source_storage_place_full_display = serializers.SerializerMethodField()
    quantity_to_move = serializers.SerializerMethodField()

    class Meta:
        model = MovementPlanItem
        fields = [
            "id",
            "warehouse_unit_id",
            "inventory_item_id",
            "inventory_item_name",
            "source_location_code",
            "source_location_name",
            "source_storage_place_display_name",
            "source_storage_place_full_display",
            "quantity_to_move",
            "reserved_quantity",
            "move_quantity",
            "remainder_quantity",
            "requires_split",
        ]
        
    def get_source_location_code(self, obj):
        unit = obj.warehouse_unit

        if unit.location is not None:
            return unit.location.code

        if unit.storage_place is not None:
            return unit.storage_place.location.code

        return None

    def get_source_location_name(self, obj):
        unit = obj.warehouse_unit

        if unit.location is not None:
            return unit.location.name

        if unit.storage_place is not None:
            return unit.storage_place.location.name

        return None

    def get_source_storage_place_display_name(self, obj):
        unit = obj.warehouse_unit

        if unit.storage_place is None:
            return None

        return unit.storage_place.get_display_name()

    def get_source_storage_place_full_display(self, obj):
        unit = obj.warehouse_unit

        if unit.storage_place is None:
            return None

        return unit.storage_place.get_display_name_verbose()

    def get_quantity_to_move(self, obj):
        if obj.requires_split:
            return obj.move_quantity

        return obj.reserved_quantity
        

class MovementPlanLineSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    unit_symbol = serializers.CharField(read_only=True)


class MovementPlanListSerializer(serializers.ModelSerializer):
    target_location_code = serializers.SerializerMethodField()
    target_location_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    days_delta = serializers.SerializerMethodField()
    planned_status_text = serializers.SerializerMethodField()
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
            "is_overdue",
            "days_delta",
            "planned_status_text",
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
        
    def _get_planned_days_delta(self, obj):
        if obj.status != MovementPlan.Status.ACTIVE or obj.planned_at is None:
            return None

        today = timezone.localdate()
        planned_date = timezone.localtime(obj.planned_at).date()

        return (planned_date - today).days

    def get_is_overdue(self, obj):
        days_delta = self._get_planned_days_delta(obj)
        return days_delta is not None and days_delta < 0

    def get_days_delta(self, obj):
        return self._get_planned_days_delta(obj)

    def get_planned_status_text(self, obj):
        days_delta = self._get_planned_days_delta(obj)

        if days_delta is None:
            return None

        if days_delta < 0:
            return f"Просрочено на {abs(days_delta)} дн."

        if days_delta == 0:
            return "Сьогодні"

        return f"Осталось {days_delta} дн."


class MovementPlanSerializer(serializers.ModelSerializer):
    items = MovementPlanItemSerializer(many=True, read_only=True)
    lines = serializers.SerializerMethodField()
    target_location_code = serializers.SerializerMethodField()
    target_location_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    days_delta = serializers.SerializerMethodField()
    planned_status_text = serializers.SerializerMethodField()
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
            "is_overdue",
            "days_delta",
            "planned_status_text",
            "comment",
            "created_at",
            "items_count",
            "lines",
            "items",
        ]
        read_only_fields = [
            "status",
            "created_by",
            "created_at",
            "lines",
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
        
    def _get_planned_days_delta(self, obj):
        if obj.status != MovementPlan.Status.ACTIVE or obj.planned_at is None:
            return None

        today = timezone.localdate()
        planned_date = timezone.localtime(obj.planned_at).date()

        return (planned_date - today).days

    def get_is_overdue(self, obj):
        days_delta = self._get_planned_days_delta(obj)
        return days_delta is not None and days_delta < 0

    def get_days_delta(self, obj):
        return self._get_planned_days_delta(obj)

    def get_planned_status_text(self, obj):
        days_delta = self._get_planned_days_delta(obj)

        if days_delta is None:
            return None

        if days_delta < 0:
            return f"Просрочено на {abs(days_delta)} дн."

        if days_delta == 0:
            return "Сьогодні"

        return f"Осталось {days_delta} дн."
        
    def get_lines(self, obj):
        lines_by_item = {}

        for item in obj.items.all():
            inventory_item = item.warehouse_unit.inventory_item
            quantity = item.move_quantity if item.requires_split else item.reserved_quantity

            if inventory_item.id not in lines_by_item:
                lines_by_item[inventory_item.id] = {
                    "inventory_item_id": inventory_item.id,
                    "inventory_item_name": inventory_item.name,
                    "quantity": quantity,
                    "unit_symbol": inventory_item.unit.symbol,
                }
            else:
                lines_by_item[inventory_item.id]["quantity"] += quantity

        return MovementPlanLineSerializer(
            lines_by_item.values(),
            many=True,
        ).data

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


class UpdateMovementPlanSerializer(serializers.Serializer):
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


class RemoveMovementPlanItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(min_value=1)


class ChangeMovementPlanItemQuantitySerializer(serializers.Serializer):
    item_id = serializers.IntegerField(min_value=1)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    
class ChangeMovementPlanInventoryItemQuantitySerializer(serializers.Serializer):
    inventory_item = serializers.PrimaryKeyRelatedField(
        queryset=InvItem.objects.filter(is_active=True)
    )
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )


class RemoveMovementPlanInventoryItemSerializer(serializers.Serializer):
    inventory_item = serializers.PrimaryKeyRelatedField(
        queryset=InvItem.objects.filter(is_active=True)
    )