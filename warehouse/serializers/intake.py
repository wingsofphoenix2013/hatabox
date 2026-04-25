from rest_framework import serializers

from orders.models import ExternalReceiptItem, TollingReceiptItem
from ..models import WarehouseLocation

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

class WarehouseTollingPendingIntakeItemSerializer(serializers.ModelSerializer):
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

    organization_id = serializers.IntegerField(
        source="order_item.order.organization.id",
        read_only=True,
    )
    organization_name = serializers.CharField(
        source="order_item.order.organization.name",
        read_only=True,
    )

    source_order_item_id = serializers.IntegerField(
        source="order_item.id",
        read_only=True,
    )

    inventory_item_id = serializers.IntegerField(
        source="order_item.inv_item.id",
        read_only=True,
    )
    inventory_item_code = serializers.CharField(
        source="order_item.inv_item.internal_code",
        read_only=True,
    )
    inventory_item_name = serializers.CharField(
        source="order_item.inv_item.name",
        read_only=True,
    )
    inventory_item_unit_id = serializers.IntegerField(
        source="order_item.inv_item.unit.id",
        read_only=True,
    )
    inventory_item_unit_name = serializers.CharField(
        source="order_item.inv_item.unit.name",
        read_only=True,
    )
    inventory_item_unit_symbol = serializers.CharField(
        source="order_item.inv_item.unit.symbol",
        read_only=True,
    )
    inventory_item_requires_storage_place = serializers.BooleanField(
        source="order_item.inv_item.requires_storage_place",
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
        model = TollingReceiptItem
        fields = [
            "id",
            "receipt_document_id",
            "receipt_no",
            "receipt_date",
            "order_id",
            "order_no",
            "order_created_at",
            "organization_id",
            "organization_name",
            "source_order_item_id",
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


class WarehouseAcceptConvertedPendingIntakeSerializer(serializers.Serializer):
    location = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseLocation.objects.filter(is_active=True)
    )
    target_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate_target_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Кількість для складу повинна бути більше 0."
            )

        return value


class WarehouseBulkAcceptPendingIntakeSerializer(serializers.Serializer):
    location = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseLocation.objects.filter(is_active=True)
    )
    receipt_item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

class WarehousePendingIntakeStatusSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    hasPendingIntake = serializers.BooleanField(read_only=True)