from rest_framework import serializers


class ProductionOrderRegistrySerializer(serializers.Serializer):
    sales_order_created_at = serializers.DateTimeField(read_only=True)

    sales_order = serializers.IntegerField(read_only=True)

    production_order = serializers.IntegerField(read_only=True)
    production_order_status = serializers.CharField(read_only=True)
    production_order_status_display = serializers.CharField(read_only=True)

    organization = serializers.IntegerField(read_only=True)
    organization_name = serializers.CharField(read_only=True)

    product = serializers.IntegerField(read_only=True)
    product_code = serializers.CharField(read_only=True)

    product_family = serializers.IntegerField(read_only=True)
    product_family_name = serializers.CharField(read_only=True)

    serial_number = serializers.CharField(read_only=True, allow_null=True)

    current_step = serializers.IntegerField(read_only=True, allow_null=True)
    current_production_order_step = serializers.IntegerField(read_only=True, allow_null=True)
    current_step_name = serializers.CharField(read_only=True, allow_null=True)
    current_step_status = serializers.CharField(read_only=True, allow_null=True)
    current_step_status_display = serializers.CharField(read_only=True, allow_null=True)
    current_step_sequence_number = serializers.IntegerField(read_only=True, allow_null=True)

    current_step_components_transferred = serializers.BooleanField(read_only=True)

    current_step_expected_finished_at = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    current_step_is_overdue = serializers.BooleanField(read_only=True)
    current_step_days_left = serializers.IntegerField(read_only=True, allow_null=True)