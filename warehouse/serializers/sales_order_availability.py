from rest_framework import serializers


class WarehouseSalesOrderAvailabilityComponentSerializer(serializers.Serializer):
    component_id = serializers.IntegerField(read_only=True)

    inv_item = serializers.IntegerField(read_only=True)
    inv_item_code = serializers.CharField(read_only=True)
    inv_item_name = serializers.CharField(read_only=True)

    required_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    fulfillment_mode = serializers.CharField(read_only=True)

    customer_available_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    donor_available_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    own_available_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    total_available_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    missing_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    can_cover = serializers.BooleanField(read_only=True)


class WarehouseSalesOrderAvailabilitySerializer(serializers.Serializer):
    sales_order = serializers.IntegerField(read_only=True)

    can_confirm = serializers.BooleanField(read_only=True)

    components = WarehouseSalesOrderAvailabilityComponentSerializer(
        many=True,
        read_only=True,
    )