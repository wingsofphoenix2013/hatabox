from decimal import Decimal

from rest_framework import serializers

from .models import (
    ExternalOrder,
    ExternalOrderItem,
    ExternalPaymentDocument,
    ExternalReceiptDocument,
    ExternalReceiptItem,
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
            total += receipt_item.received_quantity
        return total

    def get_remaining_quantity(self, obj):
        received_quantity = self.get_received_quantity(obj)
        return obj.quantity - received_quantity


class ExternalOrderItemNestedSerializer(ExternalOrderItemSerializer):
    class Meta(ExternalOrderItemSerializer.Meta):
        fields = ExternalOrderItemSerializer.Meta.fields


class ExternalPaymentDocumentSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(source="order.order_no", read_only=True)
    order_vendor_id = serializers.IntegerField(source="order.vendor.id", read_only=True)
    order_vendor_code = serializers.CharField(source="order.vendor.code", read_only=True)
    order_vendor_name = serializers.CharField(source="order.vendor.name", read_only=True)

    status_name = serializers.CharField(source="get_status_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = ExternalPaymentDocument
        fields = [
            "id",
            "payment_no",
            "order",
            "order_no",
            "order_vendor_id",
            "order_vendor_code",
            "order_vendor_name",
            "status",
            "status_name",
            "payment_amount",
            "payment_date",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "comment",
        ]
        read_only_fields = ("created_by", "created_at", "updated_at")


class ExternalReceiptItemSerializer(serializers.ModelSerializer):
    receipt_no = serializers.CharField(source="receipt_document.receipt_no", read_only=True)
    order_id = serializers.IntegerField(source="order_item.order.id", read_only=True)
    order_no = serializers.CharField(source="order_item.order.order_no", read_only=True)

    order_item_vendor_item_id = serializers.IntegerField(source="order_item.vendor_item.id", read_only=True)
    order_item_vendor_item_name = serializers.CharField(source="order_item.vendor_item.name", read_only=True)
    order_item_vendor_item_sku = serializers.CharField(source="order_item.vendor_item.vendor_sku", read_only=True)

    order_item_inv_item_id = serializers.IntegerField(source="order_item.vendor_item.item.id", read_only=True)
    order_item_inv_item_internal_code = serializers.CharField(
        source="order_item.vendor_item.item.internal_code",
        read_only=True,
    )
    order_item_inv_item_name = serializers.CharField(
        source="order_item.vendor_item.item.name",
        read_only=True,
    )
    order_item_inv_item_unit_id = serializers.IntegerField(
        source="order_item.vendor_item.item.unit.id",
        read_only=True,
    )
    order_item_inv_item_unit_name = serializers.CharField(
        source="order_item.vendor_item.item.unit.name",
        read_only=True,
    )
    order_item_inv_item_unit_symbol = serializers.CharField(
        source="order_item.vendor_item.item.unit.symbol",
        read_only=True,
    )

    class Meta:
        model = ExternalReceiptItem
        fields = [
            "id",
            "receipt_document",
            "receipt_no",
            "order_item",
            "order_id",
            "order_no",
            "order_item_vendor_item_id",
            "order_item_vendor_item_name",
            "order_item_vendor_item_sku",
            "order_item_inv_item_id",
            "order_item_inv_item_internal_code",
            "order_item_inv_item_name",
            "order_item_inv_item_unit_id",
            "order_item_inv_item_unit_name",
            "order_item_inv_item_unit_symbol",
            "received_quantity",
        ]


class ExternalReceiptItemNestedSerializer(ExternalReceiptItemSerializer):
    class Meta(ExternalReceiptItemSerializer.Meta):
        fields = ExternalReceiptItemSerializer.Meta.fields


class ExternalReceiptDocumentSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(source="order.order_no", read_only=True)
    order_vendor_id = serializers.IntegerField(source="order.vendor.id", read_only=True)
    order_vendor_code = serializers.CharField(source="order.vendor.code", read_only=True)
    order_vendor_name = serializers.CharField(source="order.vendor.name", read_only=True)

    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    items = ExternalReceiptItemNestedSerializer(many=True, read_only=True)

    class Meta:
        model = ExternalReceiptDocument
        fields = [
            "id",
            "receipt_no",
            "order",
            "order_no",
            "order_vendor_id",
            "order_vendor_code",
            "order_vendor_name",
            "receipt_date",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "comment",
            "items",
        ]
        read_only_fields = ("created_by", "created_at", "updated_at")


class ExternalOrderSerializer(serializers.ModelSerializer):
    vendor_code = serializers.CharField(source="vendor.code", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    status_name = serializers.CharField(source="get_status_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    items = ExternalOrderItemNestedSerializer(many=True, read_only=True)

    items_total_amount = serializers.SerializerMethodField()
    order_total_amount = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    receipt_state = serializers.SerializerMethodField()
    receipt_state_name = serializers.SerializerMethodField()

    class Meta:
        model = ExternalOrder
        fields = [
            "id",
            "order_no",
            "vendor",
            "vendor_code",
            "vendor_name",
            "status",
            "status_name",
            "discount_amount",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "comment",
            "items_total_amount",
            "order_total_amount",
            "paid_amount",
            "remaining_amount",
            "receipt_state",
            "receipt_state_name",
            "items",
        ]
        read_only_fields = ("created_by", "created_at", "updated_at")

    def get_items_total_amount(self, obj):
        total = Decimal("0.00")
        items = getattr(obj, "prefetched_items", None)
        if items is None:
            items = obj.items.all()

        for item in items:
            total += item.quantity * item.agreed_price
        return total

    def get_order_total_amount(self, obj):
        return self.get_items_total_amount(obj) - obj.discount_amount

    def get_paid_amount(self, obj):
        total = Decimal("0.00")
        payment_documents = getattr(obj, "prefetched_payment_documents", None)
        if payment_documents is None:
            payment_documents = obj.payment_documents.all()

        for payment_document in payment_documents:
            if payment_document.status == ExternalPaymentDocument.StatusChoices.PAID:
                total += payment_document.payment_amount
        return total

    def get_remaining_amount(self, obj):
        return self.get_order_total_amount(obj) - self.get_paid_amount(obj)

    def _get_receipt_progress(self, obj):
        items = getattr(obj, "prefetched_items", None)
        if items is None:
            items = obj.items.all()

        total_ordered = Decimal("0.000")
        total_received = Decimal("0.000")

        for item in items:
            total_ordered += item.quantity

            receipt_items = getattr(item, "prefetched_receipt_items", None)
            if receipt_items is None:
                receipt_items = item.receipt_items.all()

            for receipt_item in receipt_items:
                total_received += receipt_item.received_quantity

        return total_ordered, total_received

    def get_receipt_state(self, obj):
        total_ordered, total_received = self._get_receipt_progress(obj)

        if total_received == 0:
            return "not_received"
        if total_received < total_ordered:
            return "partially_received"
        return "fully_received"

    def get_receipt_state_name(self, obj):
        state = self.get_receipt_state(obj)

        if state == "not_received":
            return "Не отримано"
        if state == "partially_received":
            return "Частково отримано"
        return "Отримано повністю"