from datetime import date
from decimal import Decimal

from rest_framework import serializers

from orders.models import (
    ExternalOrder,
    ExternalPaymentDocument,
    ReclamationReturnDocument,
)

from .external_order_items import ExternalOrderItemNestedSerializer
from .external_payments import (
    ExternalPaymentDocumentShortSerializer,
    ExternalRefundDocumentSerializer,
)

PAYMENT_COMPLETION_TOLERANCE = Decimal("0.01")

class ExternalOrderRegisterLightSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    status_name = serializers.CharField(source="get_status_display", read_only=True)

    order_total_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=4,
        read_only=True,
    )
    payment_percent = serializers.IntegerField(read_only=True)
    receipt_percent = serializers.IntegerField(read_only=True)
    is_receipt_overdue = serializers.BooleanField(read_only=True)

    receipt_overdue_days = serializers.SerializerMethodField()
    receipt_expected_days = serializers.SerializerMethodField()

    class Meta:
        model = ExternalOrder
        fields = [
            "id",
            "order_no",
            "vendor",
            "vendor_name",
            "status",
            "status_name",
            "created_at",
            "comment",
            "has_reclamation",
            "order_total_amount",
            "payment_percent",
            "receipt_percent",
            "is_receipt_overdue",
            "receipt_overdue_days",
            "receipt_expected_days",
        ]
        read_only_fields = fields

    def get_receipt_overdue_days(self, obj):
        if not obj.is_receipt_overdue or obj.expected_delivery_date_min is None:
            return 0

        return (date.today() - obj.expected_delivery_date_min).days

    def get_receipt_expected_days(self, obj):
        if obj.receipt_percent >= 100 or obj.expected_delivery_date_min is None:
            return 0

        if date.today() > obj.expected_delivery_date_min:
            return 0

        return (obj.expected_delivery_date_min - date.today()).days


class ExternalOrderRegistrySerializer(serializers.ModelSerializer):
    vendor_code = serializers.CharField(source="vendor.code", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    status_name = serializers.CharField(source="get_status_display", read_only=True)

    order_total_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=4,
        read_only=True,
    )
    paid_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=4,
        read_only=True,
    )
    payment_percent = serializers.IntegerField(read_only=True)
    receipt_percent = serializers.IntegerField(read_only=True)
    is_receipt_overdue = serializers.BooleanField(read_only=True)

    receipt_state = serializers.SerializerMethodField()
    receipt_state_name = serializers.SerializerMethodField()
    receipt_overdue_days = serializers.SerializerMethodField()
    receipt_expected_days = serializers.SerializerMethodField()

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
            "created_at",
            "comment",
            "has_reclamation",
            "order_total_amount",
            "paid_amount",
            "payment_percent",
            "receipt_percent",
            "receipt_state",
            "receipt_state_name",
            "is_receipt_overdue",
            "receipt_overdue_days",
            "receipt_expected_days",
        ]
        read_only_fields = fields

    def get_receipt_state(self, obj):
        if obj.receipt_percent == 0:
            return "not_received"
        if obj.receipt_percent < 100:
            return "partially_received"
        return "fully_received"

    def get_receipt_state_name(self, obj):
        state = self.get_receipt_state(obj)

        if state == "not_received":
            return "Не отримано"
        if state == "partially_received":
            return "Частково отримано"
        return "Отримано повністю"

    def get_receipt_overdue_days(self, obj):
        if not obj.is_receipt_overdue or obj.expected_delivery_date_min is None:
            return 0

        return (date.today() - obj.expected_delivery_date_min).days

    def get_receipt_expected_days(self, obj):
        if obj.receipt_percent >= 100 or obj.expected_delivery_date_min is None:
            return 0

        if date.today() > obj.expected_delivery_date_min:
            return 0

        return (obj.expected_delivery_date_min - date.today()).days

class ExternalOrderReclamationReturnItemSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(
        source="warehouse_unit.inventory_item.id",
        read_only=True,
    )
    inventory_item_code = serializers.CharField(
        source="warehouse_unit.inventory_item.internal_code",
        read_only=True,
    )
    inventory_item_name = serializers.CharField(
        source="warehouse_unit.inventory_item.name",
        read_only=True,
    )
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )


class ExternalOrderReclamationReturnSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    reason_name = serializers.CharField(
        source="get_reason_display",
        read_only=True,
    )

    items = serializers.SerializerMethodField()

    class Meta:
        model = ReclamationReturnDocument
        fields = [
            "id",
            "return_no",
            "status",
            "status_name",
            "return_date",
            "reason",
            "reason_name",
            "items",
        ]

    def get_items(self, obj):
        grouped = {}

        for item in obj.items.all():
            inventory_item = item.warehouse_unit.inventory_item
            inventory_item_id = inventory_item.id

            if inventory_item_id not in grouped:
                grouped[inventory_item_id] = {
                    "inventory_item_id": inventory_item.id,
                    "inventory_item_code": inventory_item.internal_code,
                    "inventory_item_name": inventory_item.name,
                    "quantity": item.quantity,
                }
            else:
                grouped[inventory_item_id]["quantity"] += item.quantity

        return list(grouped.values())


class ExternalOrderSerializer(serializers.ModelSerializer):
    clear_image = serializers.BooleanField(write_only=True, required=False, default=False)
    vendor_code = serializers.CharField(source="vendor.code", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    status_name = serializers.CharField(source="get_status_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    items = ExternalOrderItemNestedSerializer(many=True, read_only=True)
    payment_documents = ExternalPaymentDocumentShortSerializer(
        many=True,
        read_only=True,
        source="prefetched_payment_documents",
    )

    refund_documents = ExternalRefundDocumentSerializer(
        many=True,
        read_only=True,
        source="prefetched_refund_documents",
    )

    reclamation_returns = ExternalOrderReclamationReturnSerializer(
        many=True,
        read_only=True,
    )

    items_total_amount = serializers.SerializerMethodField()
    order_total_amount = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    refunded_amount = serializers.SerializerMethodField()

    payment_percent = serializers.SerializerMethodField()
    receipt_percent = serializers.SerializerMethodField()

    receipt_state = serializers.SerializerMethodField()
    receipt_state_name = serializers.SerializerMethodField()

    is_receipt_overdue = serializers.SerializerMethodField()
    receipt_overdue_days = serializers.SerializerMethodField()
    receipt_expected_days = serializers.SerializerMethodField()
    can_start_reclamation_flow = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

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
            "prices_include_vat",
            "vat_amount",
            "discount_amount",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "comment",
            "has_reclamation",
            "can_start_reclamation_flow",
            "can_delete",
            "image",
            "clear_image",
            "items_total_amount",
            "order_total_amount",
            "paid_amount",
            "remaining_amount",
            "refunded_amount",
            "payment_percent",
            "receipt_percent",
            "receipt_state",
            "receipt_state_name",
            "is_receipt_overdue",
            "receipt_overdue_days",
            "receipt_expected_days",
            "items",
            "payment_documents",
            "refund_documents",
            "reclamation_returns",
        ]
        read_only_fields = ("created_by", "created_at", "updated_at", "vat_amount")

    def create(self, validated_data):
        validated_data.pop("clear_image", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        clear_image = validated_data.pop("clear_image", False)

        if clear_image:
            if instance.image:
                instance.image.delete(save=False)
            validated_data["image"] = None

        return super().update(instance, validated_data)

    def validate(self, attrs):
        vendor = attrs.get("vendor")
        prices_include_vat = attrs.get("prices_include_vat")

        if self.instance is not None:
            if vendor is None:
                vendor = self.instance.vendor
            if prices_include_vat is None:
                prices_include_vat = self.instance.prices_include_vat

        if vendor is None:
            return attrs

        if not vendor.vat and prices_include_vat:
            raise serializers.ValidationError({
                "prices_include_vat": (
                    "Для постачальника, який не є платником ПДВ, "
                    "поле 'prices_include_vat' повинно бути False."
                )
            })

        return attrs
        
    def _get_annotated_value(self, obj, attr_name):
        value = getattr(obj, attr_name, None)
        if value is not None:
            return value
        return None

    def get_can_start_reclamation_flow(self, obj):
        receipt_documents = getattr(obj, "prefetched_receipt_documents", None)

        if receipt_documents is None:
            receipt_documents = obj.receipt_documents.all()

        for receipt_document in receipt_documents:
            if receipt_document.completed and receipt_document.sent_to_warehouse:
                return True

        return False

    def get_can_delete(self, obj):
        if obj.status == ExternalOrder.StatusChoices.DRAFT:
            return True

        if obj.status != ExternalOrder.StatusChoices.IN_PROGRESS:
            return False

        payment_documents = getattr(obj, "prefetched_payment_documents", None)
        if payment_documents is None:
            payment_documents = obj.payment_documents.all()

        paid_amount = Decimal("0.00")
        for payment_document in payment_documents:
            if payment_document.status == ExternalPaymentDocument.StatusChoices.PAID:
                paid_amount += payment_document.payment_amount

        refunded_amount = self.get_refunded_amount(obj)

        if paid_amount > refunded_amount + PAYMENT_COMPLETION_TOLERANCE:
            return False

        receipt_documents = getattr(obj, "prefetched_receipt_documents", None)
        if receipt_documents is None:
            receipt_documents = obj.receipt_documents.all()

        if receipt_documents:
            return False

        reclamation_returns = getattr(obj, "prefetched_reclamation_returns", None)
        if reclamation_returns is None:
            reclamation_returns = obj.reclamation_returns.all()

        if reclamation_returns:
            return False

        return True

    def get_items_total_amount(self, obj):
        annotated = self._get_annotated_value(obj, "items_total_amount")
        if annotated is not None:
            return annotated

        total = Decimal("0.00")
        items = getattr(obj, "prefetched_items", None)
        if items is None:
            items = obj.items.all()

        for item in items:
            total += item.quantity * item.agreed_price
        return total

    def get_order_total_amount(self, obj):
        annotated = self._get_annotated_value(obj, "order_total_amount")
        if annotated is not None:
            return annotated

        return self.get_items_total_amount(obj) - obj.discount_amount

    def get_paid_amount(self, obj):
        annotated = self._get_annotated_value(obj, "paid_amount")
        if annotated is not None:
            return annotated

        total = Decimal("0.00")
        payment_documents = getattr(obj, "prefetched_payment_documents", None)
        if payment_documents is None:
            payment_documents = obj.payment_documents.all()

        for payment_document in payment_documents:
            if payment_document.status == ExternalPaymentDocument.StatusChoices.PAID:
                total += payment_document.payment_amount
        return total

    def get_refunded_amount(self, obj):
        total = Decimal("0.00")
        refund_documents = getattr(obj, "prefetched_refund_documents", None)

        if refund_documents is None:
            refund_documents = obj.refund_documents.all()

        for refund_document in refund_documents:
            total += refund_document.refund_amount

        return total

    def get_remaining_amount(self, obj):
        remaining_amount = self.get_order_total_amount(obj) - self.get_paid_amount(obj)

        if abs(remaining_amount) <= PAYMENT_COMPLETION_TOLERANCE:
            return Decimal("0.00")

        return remaining_amount

    def get_payment_percent(self, obj):
        annotated = self._get_annotated_value(obj, "payment_percent")
        if annotated is not None:
            return annotated

        order_total_amount = self.get_order_total_amount(obj)
        paid_amount = self.get_paid_amount(obj)

        if order_total_amount <= 0:
            return 0

        if paid_amount + PAYMENT_COMPLETION_TOLERANCE >= order_total_amount:
            return 100

        percent = round((paid_amount / order_total_amount) * 100)
        return max(0, min(99, percent))

    def _get_receipt_progress_data(self, obj):
        items = getattr(obj, "prefetched_items", None)
        if items is None:
            items = obj.items.all()

        order_total_amount = Decimal("0.00")
        received_total_amount = Decimal("0.00")
        expected_delivery_date_min = None

        for item in items:
            line_total_amount = item.quantity * item.agreed_price
            order_total_amount += line_total_amount

            receipt_items = getattr(item, "prefetched_receipt_items", None)
            if receipt_items is None:
                receipt_items = item.receipt_items.all()

            received_quantity = Decimal("0.000")
            for receipt_item in receipt_items:
                if receipt_item.receipt_document.completed:
                    received_quantity += receipt_item.received_quantity

            capped_received_quantity = min(received_quantity, item.quantity)
            received_total_amount += capped_received_quantity * item.agreed_price

            if received_quantity < item.quantity and item.expected_delivery_date is not None:
                if (
                    expected_delivery_date_min is None
                    or item.expected_delivery_date < expected_delivery_date_min
                ):
                    expected_delivery_date_min = item.expected_delivery_date

        return {
            "order_total_amount": order_total_amount - obj.discount_amount,
            "received_total_amount": received_total_amount,
            "expected_delivery_date_min": expected_delivery_date_min,
        }

    def get_receipt_percent(self, obj):
        annotated = self._get_annotated_value(obj, "receipt_percent")
        if annotated is not None:
            return annotated

        progress = self._get_receipt_progress_data(obj)
        order_total_amount = progress["order_total_amount"]
        received_total_amount = progress["received_total_amount"]

        if order_total_amount <= 0:
            return 0

        if received_total_amount >= order_total_amount:
            return 100

        percent = round((received_total_amount / order_total_amount) * 100)
        return max(0, min(99, percent))

    def get_receipt_state(self, obj):
        receipt_percent = self.get_receipt_percent(obj)

        if receipt_percent == 0:
            return "not_received"
        if receipt_percent < 100:
            return "partially_received"
        return "fully_received"

    def get_receipt_state_name(self, obj):
        state = self.get_receipt_state(obj)

        if state == "not_received":
            return "Не отримано"
        if state == "partially_received":
            return "Частково отримано"
        return "Отримано повністю"

    def get_is_receipt_overdue(self, obj):
        annotated = self._get_annotated_value(obj, "is_receipt_overdue")
        if annotated is not None:
            return annotated

        receipt_percent = self.get_receipt_percent(obj)
        if receipt_percent >= 100:
            return False

        progress = self._get_receipt_progress_data(obj)
        expected_delivery_date_min = progress["expected_delivery_date_min"]

        if expected_delivery_date_min is None:
            return False

        return date.today() > expected_delivery_date_min

    def get_receipt_overdue_days(self, obj):
        if not self.get_is_receipt_overdue(obj):
            return 0

        expected_delivery_date_min = getattr(obj, "expected_delivery_date_min", None)
        if expected_delivery_date_min is None:
            progress = self._get_receipt_progress_data(obj)
            expected_delivery_date_min = progress["expected_delivery_date_min"]

        return (date.today() - expected_delivery_date_min).days

    def get_receipt_expected_days(self, obj):
        receipt_percent = self.get_receipt_percent(obj)
        if receipt_percent >= 100:
            return 0

        expected_delivery_date_min = getattr(obj, "expected_delivery_date_min", None)
        if expected_delivery_date_min is None:
            progress = self._get_receipt_progress_data(obj)
            expected_delivery_date_min = progress["expected_delivery_date_min"]

        if expected_delivery_date_min is None:
            return 0

        if date.today() > expected_delivery_date_min:
            return 0

        return (expected_delivery_date_min - date.today()).days
