from rest_framework import serializers


class WarehouseShortageOverviewRowSerializer(serializers.Serializer):
    inv_item = serializers.IntegerField(read_only=True)

    inv_item_code = serializers.CharField(read_only=True)
    inv_item_name = serializers.CharField(read_only=True)

    inventory_item_unit_symbol = serializers.CharField(read_only=True)

    fulfillment_mode = serializers.CharField(read_only=True)

    is_required_for_start = serializers.BooleanField(read_only=True)

    missing_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    forecast_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    has_unconverted_incoming = serializers.BooleanField(read_only=True)

    net_missing_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    sales_orders_count = serializers.IntegerField(read_only=True)

    components_count = serializers.IntegerField(read_only=True)

    blocks_confirmation = serializers.BooleanField(read_only=True)