from rest_framework import serializers


class WarehouseShortageDetailSummarySerializer(serializers.Serializer):
    total_missing_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    customer_missing_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    mixed_missing_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    sales_orders_count = serializers.IntegerField(read_only=True)


class WarehouseShortageDetailRowSerializer(serializers.Serializer):
    shortage_id = serializers.IntegerField(read_only=True)

    sales_order = serializers.IntegerField(read_only=True)
    sales_order_status = serializers.CharField(read_only=True)

    sales_order_created_at = serializers.DateTimeField(
        read_only=True,
    )

    organization = serializers.IntegerField(read_only=True)
    organization_name = serializers.CharField(read_only=True)

    product = serializers.IntegerField(read_only=True)
    product_code = serializers.CharField(read_only=True)
    product_name = serializers.CharField(read_only=True)

    component_id = serializers.IntegerField(read_only=True)

    fulfillment_mode = serializers.CharField(read_only=True)

    missing_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    last_checked_at = serializers.DateTimeField(read_only=True)


class WarehouseShortageDetailSerializer(serializers.Serializer):
    inv_item = serializers.IntegerField(read_only=True)

    inv_item_code = serializers.CharField(read_only=True)
    inv_item_name = serializers.CharField(read_only=True)

    inventory_item_unit_symbol = serializers.CharField(read_only=True)

    summary = WarehouseShortageDetailSummarySerializer(
        read_only=True,
    )

    rows = WarehouseShortageDetailRowSerializer(
        many=True,
        read_only=True,
    )