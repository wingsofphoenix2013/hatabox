from rest_framework import serializers


class WarehouseProductionReservationListSerializer(serializers.Serializer):
    serial_number = serializers.CharField(
        read_only=True,
        allow_null=True,
    )

    inv_item = serializers.IntegerField(read_only=True)
    inv_item_code = serializers.CharField(read_only=True)
    inv_item_name = serializers.CharField(read_only=True)
    unit_symbol = serializers.CharField(read_only=True)

    organization = serializers.IntegerField(read_only=True)
    organization_name = serializers.CharField(read_only=True)
    product_name = serializers.CharField(read_only=True)
    product_code = serializers.CharField(read_only=True)

    source_product_step = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    source_product_step_name = serializers.CharField(
        read_only=True,
        allow_null=True,
    )

    production_order_step = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    production_order_step_status = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    production_order_step_status_display = serializers.CharField(
        read_only=True,
        allow_null=True,
    )

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    reservation_status = serializers.CharField(read_only=True)

    sales_order = serializers.IntegerField(read_only=True)
    production_order = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )

