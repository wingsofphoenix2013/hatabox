from rest_framework import serializers


class ProductionOrderStepScheduleItemSerializer(serializers.Serializer):
    production_order_step = serializers.IntegerField(min_value=1)

    expected_finished_at = serializers.DateTimeField(
        allow_null=True,
    )


class UpdateProductionOrderStepsScheduleSerializer(serializers.Serializer):
    steps = ProductionOrderStepScheduleItemSerializer(
        many=True,
        allow_empty=False,
    )