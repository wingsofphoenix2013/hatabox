from rest_framework import serializers


class WarehouseShortageDetailSummarySerializer(serializers.Serializer):
    required_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    available_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    missing_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    sales_orders_count = serializers.IntegerField(read_only=True)

    last_recalculated_at = serializers.DateTimeField(read_only=True)


class WarehouseShortageDetailRowSerializer(serializers.Serializer):
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

    required_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )


class WarehouseShortageAllocationSerializer(serializers.Serializer):
    reservation = serializers.IntegerField(read_only=True)
    reservation_status = serializers.CharField(read_only=True)

    warehouse_unit = serializers.IntegerField(read_only=True)
    warehouse_unit_status = serializers.CharField(read_only=True)

    sales_order = serializers.IntegerField(read_only=True)

    product = serializers.IntegerField(read_only=True)
    product_code = serializers.CharField(read_only=True)
    product_name = serializers.CharField(read_only=True)

    production_order = serializers.IntegerField(read_only=True)
    production_order_step = serializers.IntegerField(read_only=True)
    production_order_step_name = serializers.CharField(read_only=True)

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )


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

    allocations = WarehouseShortageAllocationSerializer(
        many=True,
        read_only=True,
    )