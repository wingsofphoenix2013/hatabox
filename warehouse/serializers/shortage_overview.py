from rest_framework import serializers


class WarehouseShortageOverviewRowSerializer(serializers.Serializer):
    inv_item = serializers.IntegerField(read_only=True)

    inv_item_code = serializers.CharField(read_only=True)
    inv_item_name = serializers.CharField(read_only=True)

    inventory_item_unit_symbol = serializers.CharField(read_only=True)

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

    reserved_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    forecast_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    has_unconverted_incoming = serializers.BooleanField(
        read_only=True,
    )

    last_recalculated_at = serializers.DateTimeField(
        read_only=True,
    )