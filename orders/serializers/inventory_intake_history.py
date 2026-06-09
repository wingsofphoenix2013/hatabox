from rest_framework import serializers


class InventoryIntakeHistoryItemSerializer(serializers.Serializer):
    source_type = serializers.CharField()

    supplier_id = serializers.IntegerField()
    supplier_name = serializers.CharField()

    order_id = serializers.IntegerField()
    order_no = serializers.CharField()
    order_created_at = serializers.DateTimeField()

    order_item_id = serializers.IntegerField()

    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)

    converted_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        allow_null=True,
        required=False,
    )

    unit_id = serializers.IntegerField()
    unit_name = serializers.CharField()
    unit_symbol = serializers.CharField()

    requires_unit_conversion = serializers.BooleanField()

    agreed_price = serializers.DecimalField(
        max_digits=14,
        decimal_places=4,
        allow_null=True,
        required=False,
    )

    actual_delivery_date = serializers.DateField(
        allow_null=True,
        required=False,
    )