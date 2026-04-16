from rest_framework import serializers

from .models import WarehouseLocation, WarehouseStoragePlace, WarehouseUnit

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


class WarehouseStoragePlaceSerializer(serializers.ModelSerializer):
    location_code = serializers.CharField(source="location.code", read_only=True)
    parent_code = serializers.CharField(source="parent.code", read_only=True)
    parent_display_name = serializers.CharField(source="parent.get_display_name", read_only=True)
    place_type_name = serializers.CharField(source="get_place_type_display", read_only=True)
    display_name = serializers.CharField(source="get_display_name", read_only=True)

    class Meta:
        model = WarehouseStoragePlace
        fields = [
            "id",
            "location",
            "location_code",
            "parent",
            "parent_code",
            "parent_display_name",
            "place_type",
            "place_type_name",
            "code",
            "name",
            "comment",
            "qr_code",
            "image",
            "is_active",
            "display_name",
        ]
        read_only_fields = ("code", "qr_code", "display_name")

class WarehouseUnitSerializer(serializers.ModelSerializer):
    inventory_item_code = serializers.CharField(
        source="inventory_item.internal_code",
        read_only=True,
    )
    inventory_item_name = serializers.CharField(
        source="inventory_item.name",
        read_only=True,
    )
    inventory_item_unit_name = serializers.CharField(
        source="inventory_item.unit.name",
        read_only=True,
    )
    inventory_item_unit_symbol = serializers.CharField(
        source="inventory_item.unit.symbol",
        read_only=True,
    )

    location_code = serializers.CharField(
        source="location.code",
        read_only=True,
    )
    storage_place_code = serializers.CharField(
        source="storage_place.code",
        read_only=True,
    )
    storage_place_display_name = serializers.CharField(
        source="storage_place.get_display_name",
        read_only=True,
    )

    source_order_no = serializers.CharField(
        source="source_order_item.order.order_no",
        read_only=True,
    )
    source_vendor_item_name = serializers.CharField(
        source="source_order_item.vendor_item.name",
        read_only=True,
    )

    class Meta:
        model = WarehouseUnit
        fields = [
            "id",
            "inventory_item",
            "inventory_item_code",
            "inventory_item_name",
            "inventory_item_unit_name",
            "inventory_item_unit_symbol",
            "location",
            "location_code",
            "storage_place",
            "storage_place_code",
            "storage_place_display_name",
            "quantity",
            "source_receipt_item",
            "source_order_item",
            "source_order_no",
            "source_vendor_item_name",
            "is_active",
            "created_at",
            "updated_at",
        ]