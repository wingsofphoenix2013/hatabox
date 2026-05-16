from decimal import Decimal

from rest_framework import serializers

from orders.models import (
    ExternalOrder,
    ExternalOrderItem,
)


class ExternalOrderItemSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(source="order.order_no", read_only=True)

    vendor_item_vendor_id = serializers.IntegerField(source="vendor_item.vendor.id", read_only=True)
    vendor_item_vendor_code = serializers.CharField(source="vendor_item.vendor.code", read_only=True)
    vendor_item_vendor_name = serializers.CharField(source="vendor_item.vendor.name", read_only=True)

    vendor_item_inv_item_id = serializers.IntegerField(source="vendor_item.item.id", read_only=True)
    vendor_item_inv_item_internal_code = serializers.CharField(source="vendor_item.item.internal_code", read_only=True)
    vendor_item_inv_item_name = serializers.CharField(source="vendor_item.item.name", read_only=True)
    vendor_item_inv_item_description = serializers.CharField(source="vendor_item.item.description", read_only=True)
    vendor_item_inv_item_category_id = serializers.IntegerField(source="vendor_item.item.category.id", read_only=True)
    vendor_item_inv_item_category_name = serializers.CharField(source="vendor_item.item.category.name", read_only=True)
    vendor_item_inv_item_unit_id = serializers.IntegerField(source="vendor_item.item.unit.id", read_only=True)
    vendor_item_inv_item_unit_name = serializers.CharField(source="vendor_item.item.unit.name", read_only=True)
    vendor_item_inv_item_unit_symbol = serializers.CharField(source="vendor_item.item.unit.symbol", read_only=True)

    vendor_item_name = serializers.CharField(source="vendor_item.name", read_only=True)
    vendor_item_sku = serializers.CharField(source="vendor_item.vendor_sku", read_only=True)

    vendor_item_brand_id = serializers.IntegerField(source="vendor_item.brand.id", read_only=True)
    vendor_item_brand_name = serializers.CharField(source="vendor_item.brand.name", read_only=True)

    vendor_item_country_of_origin_id = serializers.IntegerField(
        source="vendor_item.country_of_origin.id",
        read_only=True,
    )
    vendor_item_country_of_origin_name = serializers.CharField(
        source="vendor_item.country_of_origin.name",
        read_only=True,
    )
    vendor_item_country_of_origin_code = serializers.CharField(
        source="vendor_item.country_of_origin.code",
        read_only=True,
    )

    line_total_amount = serializers.SerializerMethodField()
    received_quantity = serializers.SerializerMethodField()
    remaining_quantity = serializers.SerializerMethodField()

    class Meta:
        model = ExternalOrderItem
        fields = [
            "id",
            "order",
            "order_no",
            "vendor_item",
            "vendor_item_vendor_id",
            "vendor_item_vendor_code",
            "vendor_item_vendor_name",
            "vendor_item_inv_item_id",
            "vendor_item_inv_item_internal_code",
            "vendor_item_inv_item_name",
            "vendor_item_inv_item_description",
            "vendor_item_inv_item_category_id",
            "vendor_item_inv_item_category_name",
            "vendor_item_inv_item_unit_id",
            "vendor_item_inv_item_unit_name",
            "vendor_item_inv_item_unit_symbol",
            "vendor_item_name",
            "vendor_item_sku",
            "vendor_item_brand_id",
            "vendor_item_brand_name",
            "vendor_item_country_of_origin_id",
            "vendor_item_country_of_origin_name",
            "vendor_item_country_of_origin_code",
            "quantity",
            "agreed_price",
            "requires_unit_conversion",
            "expected_delivery_date",
            "line_total_amount",
            "received_quantity",
            "remaining_quantity",
        ]

    def get_line_total_amount(self, obj):
        return obj.quantity * obj.agreed_price

    def get_received_quantity(self, obj):
        total = Decimal("0.000")
        receipt_items = getattr(obj, "prefetched_receipt_items", None)
        if receipt_items is None:
            receipt_items = obj.receipt_items.all()

        for receipt_item in receipt_items:
            if receipt_item.receipt_document.completed:
                total += receipt_item.received_quantity
        return total

    def get_remaining_quantity(self, obj):
        received_quantity = self.get_received_quantity(obj)
        return obj.quantity - received_quantity

    def validate(self, attrs):
        order = attrs.get("order")
        vendor_item = attrs.get("vendor_item")

        if self.instance is not None:
            order = self.instance.order

            if vendor_item is None:
                vendor_item = self.instance.vendor_item

        if order is None:
            return attrs

        if order.status != ExternalOrder.StatusChoices.DRAFT:
            if (
                self.instance is not None
                and order.status == ExternalOrder.StatusChoices.IN_PROGRESS
                and set(attrs.keys()) == {"expected_delivery_date"}
            ):
                return attrs

            raise serializers.ValidationError(
                "Після виходу замовлення з чернетки можна змінювати лише очікувану дату поставки."
            )

        if vendor_item is not None and vendor_item.vendor_id != order.vendor_id:
            raise serializers.ValidationError(
                "Товар постачальника повинен належати тому ж постачальнику, що і замовлення."
            )

        return attrs


class ExternalOrderItemNestedSerializer(ExternalOrderItemSerializer):
    class Meta(ExternalOrderItemSerializer.Meta):
        fields = ExternalOrderItemSerializer.Meta.fields