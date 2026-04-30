from rest_framework import serializers

from ..models import WarehouseLocation
from .storage_places import WarehouseStoragePlaceSerializer


class WarehouseLocationDirectStockRowSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)
    inventory_item_unit_symbol = serializers.CharField(read_only=True)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )


class WarehouseLocationDirectReservedStockRowSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)
    inventory_item_unit_symbol = serializers.CharField(read_only=True)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    movement_plan_id = serializers.IntegerField(read_only=True)
    movement_plan_status = serializers.CharField(read_only=True)
    movement_plan_planned_at = serializers.DateTimeField(read_only=True, allow_null=True)
    movement_plan_is_overdue = serializers.BooleanField(read_only=True)
    movement_plan_days_delta = serializers.IntegerField(read_only=True, allow_null=True)
    movement_plan_planned_status_text = serializers.CharField(read_only=True, allow_null=True)
    target_location_id = serializers.IntegerField(read_only=True)
    target_location_code = serializers.CharField(read_only=True)
    target_location_name = serializers.CharField(read_only=True)
    target_storage_place_id = serializers.IntegerField(read_only=True, allow_null=True)
    target_storage_place_code = serializers.CharField(read_only=True, allow_null=True)
    target_storage_place_display_name = serializers.CharField(read_only=True, allow_null=True)
    target_storage_place_full_display = serializers.CharField(read_only=True, allow_null=True)


class WarehouseLocationDetailSerializer(serializers.Serializer):
    location = serializers.DictField(read_only=True)
    storage_places = WarehouseStoragePlaceSerializer(
        many=True,
        read_only=True,
    )
    direct_stock = WarehouseLocationDirectStockRowSerializer(
        many=True,
        read_only=True,
    )
    direct_reserved_stock = WarehouseLocationDirectReservedStockRowSerializer(
        many=True,
        read_only=True,
    )


class WarehouseLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseLocation
        fields = [
            "id",
            "code",
            "name",
            "address",
            "comment",
            "is_active",
        ]
        read_only_fields = ("code",)