from rest_framework import serializers


class ProductionOrderDetailSummarySerializer(serializers.Serializer):
    sales_order = serializers.IntegerField(read_only=True)
    sales_order_created_at = serializers.DateTimeField(read_only=True)

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

    comment = serializers.CharField(read_only=True, allow_blank=True)

    started_at = serializers.DateTimeField(read_only=True, allow_null=True)
    expected_ready_at = serializers.DateTimeField(read_only=True, allow_null=True)
    ready_at = serializers.DateTimeField(read_only=True, allow_null=True)

    current_step = serializers.IntegerField(read_only=True, allow_null=True)
    current_production_order_step = serializers.IntegerField(read_only=True, allow_null=True)
    current_step_name = serializers.CharField(read_only=True, allow_null=True)
    current_step_status = serializers.CharField(read_only=True, allow_null=True)
    current_step_status_display = serializers.CharField(read_only=True, allow_null=True)

    current_step_components_transferred = serializers.BooleanField(read_only=True)


class ProductionOrderDetailStepSerializer(serializers.Serializer):
    production_order_step = serializers.IntegerField(read_only=True)
    source_product_step = serializers.IntegerField(read_only=True)

    name = serializers.CharField(read_only=True)

    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)

    started_at = serializers.DateTimeField(read_only=True, allow_null=True)
    expected_finished_at = serializers.DateTimeField(read_only=True, allow_null=True)
    finished_at = serializers.DateTimeField(read_only=True, allow_null=True)

    current_is_overdue = serializers.BooleanField(read_only=True)
    current_days_left = serializers.IntegerField(read_only=True, allow_null=True)

    final_is_overdue = serializers.BooleanField(read_only=True)
    final_overdue_days = serializers.IntegerField(read_only=True, allow_null=True)

    production_movement = serializers.IntegerField(read_only=True, allow_null=True)
    production_movement_status = serializers.CharField(read_only=True, allow_null=True)

    components_transferred = serializers.BooleanField(read_only=True)

    can_start = serializers.BooleanField(read_only=True)

    production_movement_invoice_file = serializers.CharField(
        read_only=True,
        allow_null=True,
    )


class ProductionOrderDetailSerializer(serializers.Serializer):
    summary = ProductionOrderDetailSummarySerializer(read_only=True)
    steps = ProductionOrderDetailStepSerializer(
        many=True,
        read_only=True,
    )