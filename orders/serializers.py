from rest_framework import serializers
from .models import ExternalOrder, ExternalOrderItem


class ExternalOrderItemSerializer(serializers.ModelSerializer):
    vendor_item_vendor_id = serializers.IntegerField(source="vendor_item.vendor.id", read_only=True)
    vendor_item_vendor_code = serializers.CharField(source="vendor_item.vendor.code", read_only=True)
    vendor_item_vendor_name = serializers.CharField(source="vendor_item.vendor.name", read_only=True)

    vendor_item_inv_item_id = serializers.IntegerField(source="vendor_item.item.id", read_only=True)
    vendor_item_inv_item_internal_code = serializers.CharField(source="vendor_item.item.internal_code", read_only=True)
    vendor_item_inv_item_name = serializers.CharField(source="vendor_item.item.name", read_only=True)
    vendor_item_inv_item_description = serializers.CharField(source="vendor_item.item.description", read_only=True)
    vendor_item_inv_item_category_id = serializers.IntegerField(source="vendor_item.item.category.id", read_only=True)
    vendor_item_inv_item_category_name = serializers.CharField(source="vendor_item.item.category.name", read_only=True)
    vendor_item_inv_item_unit_id = serializers.IntegerField(source="vendor_item.item.unit.id", read_only=True)
    vendor_item_inv_item_unit_name = serializers.CharField(source="vendor_item.item.unit.name", read_only=True)
    vendor_item_inv_item_unit_symbol = serializers.CharField(source="vendor_item.item.unit.symbol", read_only=True)

    vendor_item_name = serializers.CharField(source="vendor_item.name", read_only=True)
    vendor_item_sku = serializers.CharField(source="vendor_item.vendor_sku", read_only=True)

    vendor_item_brand_id = serializers.IntegerField(source="vendor_item.brand.id", read_only=True)
    vendor_item_brand_name = serializers.CharField(source="vendor_item.brand.name", read_only=True)

    vendor_item_country_of_origin_id = serializers.IntegerField(
        source="vendor_item.country_of_origin.id",
        read_only=True,
    )
    vendor_item_country_of_origin_name = serializers.CharField(
        source="vendor_item.country_of_origin.name",
        read_only=True,
    )
    vendor_item_country_of_origin_code = serializers.CharField(
        source="vendor_item.country_of_origin.code",
        read_only=True,
    )

    order_no = serializers.CharField(source="order.order_no", read_only=True)

    class Meta:
        model = ExternalOrderItem
        fields = [
            "id",
            "order",
            "order_no",
            "vendor_item",
            "vendor_item_vendor_id",
            "vendor_item_vendor_code",
            "vendor_item_vendor_name",
            "vendor_item_inv_item_id",
            "vendor_item_inv_item_internal_code",
            "vendor_item_inv_item_name",
            "vendor_item_inv_item_description",
            "vendor_item_inv_item_category_id",
            "vendor_item_inv_item_category_name",
            "vendor_item_inv_item_unit_id",
            "vendor_item_inv_item_unit_name",
            "vendor_item_inv_item_unit_symbol",
            "vendor_item_name",
            "vendor_item_sku",
            "vendor_item_brand_id",
            "vendor_item_brand_name",
            "vendor_item_country_of_origin_id",
            "vendor_item_country_of_origin_name",
            "vendor_item_country_of_origin_code",
            "quantity",
            "agreed_price",
            "lead_time_days",
            "expected_delivery_date",
            "is_active",
        ]


class ExternalOrderItemNestedSerializer(serializers.ModelSerializer):
    vendor_item_vendor_id = serializers.IntegerField(source="vendor_item.vendor.id", read_only=True)
    vendor_item_vendor_code = serializers.CharField(source="vendor_item.vendor.code", read_only=True)
    vendor_item_vendor_name = serializers.CharField(source="vendor_item.vendor.name", read_only=True)

    vendor_item_inv_item_id = serializers.IntegerField(source="vendor_item.item.id", read_only=True)
    vendor_item_inv_item_internal_code = serializers.CharField(source="vendor_item.item.internal_code", read_only=True)
    vendor_item_inv_item_name = serializers.CharField(source="vendor_item.item.name", read_only=True)
    vendor_item_inv_item_description = serializers.CharField(source="vendor_item.item.description", read_only=True)
    vendor_item_inv_item_category_id = serializers.IntegerField(source="vendor_item.item.category.id", read_only=True)
    vendor_item_inv_item_category_name = serializers.CharField(source="vendor_item.item.category.name", read_only=True)
    vendor_item_inv_item_unit_id = serializers.IntegerField(source="vendor_item.item.unit.id", read_only=True)
    vendor_item_inv_item_unit_name = serializers.CharField(source="vendor_item.item.unit.name", read_only=True)
    vendor_item_inv_item_unit_symbol = serializers.CharField(source="vendor_item.item.unit.symbol", read_only=True)

    vendor_item_name = serializers.CharField(source="vendor_item.name", read_only=True)
    vendor_item_sku = serializers.CharField(source="vendor_item.vendor_sku", read_only=True)

    vendor_item_brand_id = serializers.IntegerField(source="vendor_item.brand.id", read_only=True)
    vendor_item_brand_name = serializers.CharField(source="vendor_item.brand.name", read_only=True)

    vendor_item_country_of_origin_id = serializers.IntegerField(
        source="vendor_item.country_of_origin.id",
        read_only=True,
    )
    vendor_item_country_of_origin_name = serializers.CharField(
        source="vendor_item.country_of_origin.name",
        read_only=True,
    )
    vendor_item_country_of_origin_code = serializers.CharField(
        source="vendor_item.country_of_origin.code",
        read_only=True,
    )

    class Meta:
        model = ExternalOrderItem
        fields = [
            "id",
            "order",
            "vendor_item",
            "vendor_item_vendor_id",
            "vendor_item_vendor_code",
            "vendor_item_vendor_name",
            "vendor_item_inv_item_id",
            "vendor_item_inv_item_internal_code",
            "vendor_item_inv_item_name",
            "vendor_item_inv_item_description",
            "vendor_item_inv_item_category_id",
            "vendor_item_inv_item_category_name",
            "vendor_item_inv_item_unit_id",
            "vendor_item_inv_item_unit_name",
            "vendor_item_inv_item_unit_symbol",
            "vendor_item_name",
            "vendor_item_sku",
            "vendor_item_brand_id",
            "vendor_item_brand_name",
            "vendor_item_country_of_origin_id",
            "vendor_item_country_of_origin_name",
            "vendor_item_country_of_origin_code",
            "quantity",
            "agreed_price",
            "lead_time_days",
            "expected_delivery_date",
            "is_active",
        ]


class ExternalOrderSerializer(serializers.ModelSerializer):
    vendor_code = serializers.CharField(source="vendor.code", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    status_code = serializers.CharField(source="status.code", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)

    payment_status_code = serializers.CharField(source="payment_status.code", read_only=True)
    payment_status_name = serializers.CharField(source="payment_status.name", read_only=True)

    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    items = ExternalOrderItemNestedSerializer(many=True, read_only=True)

    class Meta:
        model = ExternalOrder
        fields = [
            "id",
            "order_no",
            "vendor",
            "vendor_code",
            "vendor_name",
            "status",
            "status_code",
            "status_name",
            "payment_status",
            "payment_status_code",
            "payment_status_name",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "comment",
            "is_active",
            "items",
        ]
        read_only_fields = ("created_by", "created_at", "updated_at")