from rest_framework import serializers

from ..models import WarehouseUnit

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

    source_order_no = serializers.SerializerMethodField()
    source_counterparty_name = serializers.SerializerMethodField()
    source_item_name = serializers.SerializerMethodField()

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
            "tolling_source_receipt_item",
            "tolling_source_order_item",
            "source_order_no",
            "source_counterparty_name",
            "source_item_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        
    def get_source_order_no(self, obj):
        if obj.source_order_item_id:
            return obj.source_order_item.order.order_no
        if obj.tolling_source_order_item_id:
            return obj.tolling_source_order_item.order.order_no
        return None

    def get_source_counterparty_name(self, obj):
        if obj.source_order_item_id:
            return obj.source_order_item.order.vendor.name
        if obj.tolling_source_order_item_id:
            return obj.tolling_source_order_item.order.organization.name
        return None

    def get_source_item_name(self, obj):
        if obj.source_order_item_id:
            return obj.source_order_item.vendor_item.name
        if obj.tolling_source_order_item_id:
            return obj.tolling_source_order_item.inv_item.name
        return None
