from rest_framework import serializers
from orders.models import ExternalReceiptItem
from .models import WarehouseLocation, WarehouseStoragePlace, WarehouseUnit
from inventory.models import InvItem

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
    placement_display = serializers.SerializerMethodField()
    display_name_verbose = serializers.SerializerMethodField()

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
            "placement_display",
            "display_name_verbose",
            "name",
            "comment",
            "qr_code",
            "image",
            "is_active",
            "display_name",
        ]
        read_only_fields = ("code", "qr_code", "display_name")

    def get_placement_display(self, obj):
        if obj.parent is None:
            return "На локації"

        ancestors = []
        current = obj.parent

        while current is not None:
            ancestors.append(f"{current.get_place_type_display()} {current.code}")
            current = current.parent

        ancestors.reverse()
        return ", ".join(ancestors)
        
    def get_display_name_verbose(self, obj):
        chain = []
        current = obj

        while current is not None:
            chain.append(f"{current.get_place_type_display()} {current.code}")
            current = current.parent

        chain.reverse()
        result = ", ".join(chain)

        if obj.parent is None:
            result = f"{result} на локації"

        return result

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

class WarehousePendingIntakeItemSerializer(serializers.ModelSerializer):
    receipt_document_id = serializers.IntegerField(
        source="receipt_document.id",
        read_only=True,
    )
    receipt_no = serializers.CharField(
        source="receipt_document.receipt_no",
        read_only=True,
    )
    receipt_date = serializers.DateField(
        source="receipt_document.receipt_date",
        read_only=True,
    )

    order_id = serializers.IntegerField(
        source="order_item.order.id",
        read_only=True,
    )
    order_no = serializers.CharField(
        source="order_item.order.order_no",
        read_only=True,
    )
    order_created_at = serializers.DateTimeField(
        source="order_item.order.created_at",
        read_only=True,
    )

    vendor_id = serializers.IntegerField(
        source="order_item.order.vendor.id",
        read_only=True,
    )
    vendor_code = serializers.CharField(
        source="order_item.order.vendor.code",
        read_only=True,
    )
    vendor_name = serializers.CharField(
        source="order_item.order.vendor.name",
        read_only=True,
    )

    source_order_item_id = serializers.IntegerField(
        source="order_item.id",
        read_only=True,
    )
    vendor_item_id = serializers.IntegerField(
        source="order_item.vendor_item.id",
        read_only=True,
    )
    vendor_item_name = serializers.CharField(
        source="order_item.vendor_item.name",
        read_only=True,
    )
    vendor_item_sku = serializers.CharField(
        source="order_item.vendor_item.vendor_sku",
        read_only=True,
    )

    inventory_item_id = serializers.IntegerField(
        source="order_item.vendor_item.item.id",
        read_only=True,
    )
    inventory_item_code = serializers.CharField(
        source="order_item.vendor_item.item.internal_code",
        read_only=True,
    )
    inventory_item_name = serializers.CharField(
        source="order_item.vendor_item.item.name",
        read_only=True,
    )
    inventory_item_unit_id = serializers.IntegerField(
        source="order_item.vendor_item.item.unit.id",
        read_only=True,
    )
    inventory_item_unit_name = serializers.CharField(
        source="order_item.vendor_item.item.unit.name",
        read_only=True,
    )
    inventory_item_unit_symbol = serializers.CharField(
        source="order_item.vendor_item.item.unit.symbol",
        read_only=True,
    )
    inventory_item_requires_storage_place = serializers.BooleanField(
        source="order_item.vendor_item.item.requires_storage_place",
        read_only=True,
    )

    received_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    
    requires_unit_conversion = serializers.BooleanField(
        source="order_item.requires_unit_conversion",
        read_only=True,
    )
    can_be_directly_accepted = serializers.SerializerMethodField()

    class Meta:
        model = ExternalReceiptItem
        fields = [
            "id",
            "receipt_document_id",
            "receipt_no",
            "receipt_date",
            "order_id",
            "order_no",
            "order_created_at",
            "vendor_id",
            "vendor_code",
            "vendor_name",
            "source_order_item_id",
            "vendor_item_id",
            "vendor_item_name",
            "vendor_item_sku",
            "inventory_item_id",
            "inventory_item_code",
            "inventory_item_name",
            "inventory_item_unit_id",
            "inventory_item_unit_name",
            "inventory_item_unit_symbol",
            "inventory_item_requires_storage_place",
            "received_quantity",
            "requires_unit_conversion",
            "can_be_directly_accepted",
        ]

    def get_can_be_directly_accepted(self, obj):
        return not obj.order_item.requires_unit_conversion

class WarehouseAcceptPendingIntakeSerializer(serializers.Serializer):
    location = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseLocation.objects.filter(is_active=True)
    )

class WarehouseBulkAcceptPendingIntakeSerializer(serializers.Serializer):
    location = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseLocation.objects.filter(is_active=True)
    )
    receipt_item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class WarehouseDebugPlanMoveSerializer(serializers.Serializer):
    inventory_item = serializers.PrimaryKeyRelatedField(
        queryset=InvItem.objects.all()
    )
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )