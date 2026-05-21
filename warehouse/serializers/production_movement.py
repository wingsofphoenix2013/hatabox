from rest_framework import serializers

from warehouse.models import (
    WarehouseProductionMovement,
    WarehouseProductionMovementItem,
)


class WarehouseProductionMovementItemSerializer(serializers.ModelSerializer):
    inventory_item_code = serializers.CharField(
        source="inventory_item.internal_code",
        read_only=True,
    )
    inventory_item_name = serializers.CharField(
        source="inventory_item.name",
        read_only=True,
    )
    unit_symbol = serializers.CharField(
        source="inventory_item.unit.symbol",
        read_only=True,
    )
    source_warehouse_unit_status = serializers.CharField(
        source="source_warehouse_unit.status",
        read_only=True,
    )
    result_warehouse_unit_status = serializers.CharField(
        source="result_warehouse_unit.status",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = WarehouseProductionMovementItem
        fields = [
            "id",
            "production_reservation",
            "source_warehouse_unit",
            "source_warehouse_unit_status",
            "result_warehouse_unit",
            "result_warehouse_unit_status",
            "inventory_item",
            "inventory_item_code",
            "inventory_item_name",
            "unit_symbol",
            "quantity",
            "executed_source_location",
            "executed_source_location_code",
            "executed_source_location_name",
            "executed_source_storage_place",
            "executed_source_storage_place_code",
            "executed_source_storage_place_display_name",
            "executed_source_storage_place_full_display",
        ]


class WarehouseProductionMovementListSerializer(serializers.ModelSerializer):
    production_order_serial_number = serializers.CharField(
        source="production_order.serial_number",
        read_only=True,
        allow_null=True,
    )

    product = serializers.IntegerField(
        source="production_order.sales_order.product_id",
        read_only=True,
    )

    product_code = serializers.CharField(
        source="production_order.sales_order.product.code",
        read_only=True,
    )

    product_family_name = serializers.CharField(
        source="production_order.sales_order.product.product_family.name",
        read_only=True,
    )

    production_order_step_name = serializers.CharField(
        source="production_order_step.name",
        read_only=True,
    )
    production_order_step_sequence_number = serializers.IntegerField(
        source="production_order_step.sequence_number",
        read_only=True,
    )
    sales_order = serializers.IntegerField(
        source="production_order.sales_order_id",
        read_only=True,
    )
    items_count = serializers.IntegerField(read_only=True)

    invoice_file = serializers.FileField(
        read_only=True,
        allow_null=True,
    )

    invoice_generated_at = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = WarehouseProductionMovement
        fields = [
            "id",
            "production_order",
            "production_order_serial_number",

            "sales_order",

            "product",
            "product_code",
            "product_family_name",

            "production_order_step",
            "production_order_step_name",
            "production_order_step_sequence_number",
            "status",

            "invoice_file",
            "invoice_generated_at",

            "created_by",
            "comment",
            "created_at",
            "executed_at",
            "cancelled_at",
            "items_count",
        ]


class UpdateWarehouseProductionMovementCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(
        required=True,
        allow_blank=True,
    )


class WarehouseProductionMovementSerializer(serializers.ModelSerializer):
    production_order_step_name = serializers.CharField(
        source="production_order_step.name",
        read_only=True,
    )
    production_order_step_sequence_number = serializers.IntegerField(
        source="production_order_step.sequence_number",
        read_only=True,
    )
    sales_order = serializers.IntegerField(
        source="production_order.sales_order_id",
        read_only=True,
    )
    items = WarehouseProductionMovementItemSerializer(
        many=True,
        read_only=True,
    )
    items_count = serializers.IntegerField(read_only=True)
    invoice_file = serializers.FileField(read_only=True)
    invoice_generated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = WarehouseProductionMovement
        fields = [
            "id",
            "production_order",
            "sales_order",
            "production_order_step",
            "production_order_step_name",
            "production_order_step_sequence_number",
            "status",
            "created_by",
            "comment",
            "invoice_file",
            "invoice_generated_at",
            "created_at",
            "executed_at",
            "cancelled_at",
            "items_count",
            "items",
        ]