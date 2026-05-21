from rest_framework import serializers

from warehouse.models import WarehouseProductionReservation


class WarehouseProductionReservationListSerializer(serializers.ModelSerializer):
    serial_number = serializers.SerializerMethodField()

    inv_item = serializers.IntegerField(
        source="sales_order_component.inv_item_id",
        read_only=True,
    )

    inv_item_code = serializers.CharField(
        source="sales_order_component.inv_item.internal_code",
        read_only=True,
    )

    inv_item_name = serializers.CharField(
        source="sales_order_component.inv_item.name",
        read_only=True,
    )

    unit_symbol = serializers.CharField(
        source="sales_order_component.inv_item.unit.symbol",
        read_only=True,
    )

    organization = serializers.IntegerField(
        source="sales_order.organization_id",
        read_only=True,
    )

    organization_name = serializers.CharField(
        source="sales_order.organization.name",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="sales_order.product.product_family.name",
        read_only=True,
    )

    product_code = serializers.CharField(
        source="sales_order.product.code",
        read_only=True,
    )

    source_product_step = serializers.IntegerField(
        source=(
            "production_order_step_component."
            "production_order_step."
            "source_product_step_id"
        ),
        read_only=True,
        allow_null=True,
    )

    source_product_step_name = serializers.CharField(
        source=(
            "production_order_step_component."
            "production_order_step."
            "source_product_step.name"
        ),
        read_only=True,
        allow_null=True,
    )

    sales_order = serializers.IntegerField(
        source="sales_order_id",
        read_only=True,
    )

    production_order = serializers.IntegerField(
        source=(
            "production_order_step_component."
            "production_order_step."
            "production_order_id"
        ),
        read_only=True,
        allow_null=True,
    )

    reservation_status = serializers.CharField(
        source="status",
        read_only=True,
    )

    class Meta:
        model = WarehouseProductionReservation
        fields = [
            "serial_number",

            "inv_item",
            "inv_item_code",
            "inv_item_name",
            "unit_symbol",

            "organization",
            "organization_name",
            "product_name",
            "product_code",
            "source_product_step",
            "source_product_step_name",
            "quantity",
            "reservation_status",
            "sales_order",
            "production_order",
        ]
        
    def get_serial_number(self, obj):
        try:
            return obj.sales_order.production_order.serial_number
        except obj.sales_order.production_order.RelatedObjectDoesNotExist:
            return None