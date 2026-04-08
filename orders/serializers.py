from datetime import date
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
            raise serializers.ValidationError(
                "Редагування рядків замовлення дозволене лише для замовлень у статусі 'Чернетка'."
            )

        if vendor_item is not None and vendor_item.vendor_id != order.vendor_id:
            raise serializers.ValidationError(
                "Товар постачальника повинен належати тому ж постачальнику, що і замовлення."
            )

        return attrs


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

    def validate(self, attrs):
        order = attrs.get("order")
        payment_amount = attrs.get("payment_amount")

        if self.instance is not None:
            if order is None:
                order = self.instance.order
            if payment_amount is None:
                payment_amount = self.instance.payment_amount

        if order is None:
            return attrs

        if order.status == ExternalOrder.StatusChoices.COMPLETED:
            raise serializers.ValidationError(
                "Неможливо змінювати платіжні документи для завершеного замовлення."
            )

        # 1. Запрет для draft заказа
        if order.status == ExternalOrder.StatusChoices.DRAFT:
            raise serializers.ValidationError(
                "Платіжний документ не можна створити або редагувати, поки замовлення перебуває у статусі 'Чернетка'."
            )

        # 2. Проверка суммы > 0
        if payment_amount is None or payment_amount <= 0:
            raise serializers.ValidationError(
                "Сума платіжного документа повинна бути більше 0."
            )

        # 3. Считаем сумму заказа
        items_total_amount = Decimal("0.00")
        for item in order.items.all():
            items_total_amount += item.quantity * item.agreed_price

        order_total_amount = items_total_amount - order.discount_amount

        # 4. Считаем уже существующие платежи (draft + approved + paid)
        existing_payments = ExternalPaymentDocument.objects.filter(
            order=order,
            status__in=[
                ExternalPaymentDocument.StatusChoices.DRAFT,
                ExternalPaymentDocument.StatusChoices.APPROVED,
                ExternalPaymentDocument.StatusChoices.PAID,
            ],
        )

        if self.instance is not None:
            existing_payments = existing_payments.exclude(id=self.instance.id)

        planned_total = Decimal("0.00")
        for payment in existing_payments:
            planned_total += payment.payment_amount

        # 5. Проверка превышения суммы заказа
        if planned_total + payment_amount > order_total_amount:
            raise serializers.ValidationError(
                "Сума всіх платіжних документів не може перевищувати суму замовлення."
            )

        return attrs


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

    def validate(self, attrs):
        receipt_document = attrs.get("receipt_document")
        order_item = attrs.get("order_item")
        received_quantity = attrs.get("received_quantity")

        if self.instance is not None:
            if receipt_document is None:
                receipt_document = self.instance.receipt_document
            if order_item is None:
                order_item = self.instance.order_item
            if received_quantity is None:
                received_quantity = self.instance.received_quantity

        if receipt_document is None or order_item is None or received_quantity is None:
            return attrs

        if order_item.order.status == ExternalOrder.StatusChoices.COMPLETED:
            raise serializers.ValidationError(
                "Неможливо змінювати рядки приходу для завершеного замовлення."
            )

        if receipt_document.order_id != order_item.order_id:
            raise serializers.ValidationError(
                "Рядок приходу повинен належати тому ж замовленню, що і документ приходу."
            )

        already_received = Decimal("0.000")
        receipt_items = order_item.receipt_items.all()

        for receipt_item in receipt_items:
            if self.instance is not None and receipt_item.id == self.instance.id:
                continue
            already_received += receipt_item.received_quantity

        if already_received + received_quantity > order_item.quantity:
            raise serializers.ValidationError(
                "Отримана кількість не може перевищувати замовлену кількість по рядку замовлення."
            )

        return attrs


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

    def validate(self, attrs):
        order = attrs.get("order")

        if self.instance is not None and order is None:
            order = self.instance.order

        if order is None:
            return attrs

        if order.status == ExternalOrder.StatusChoices.COMPLETED:
            raise serializers.ValidationError(
                "Неможливо змінювати документи приходу для завершеного замовлення."
            )

        if order.status == ExternalOrder.StatusChoices.DRAFT:
            raise serializers.ValidationError(
                "Документ приходу не можна створити або редагувати, поки замовлення перебуває у статусі 'Чернетка'."
            )

        return attrs

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

    payment_percent = serializers.SerializerMethodField()
    receipt_percent = serializers.SerializerMethodField()

    receipt_state = serializers.SerializerMethodField()
    receipt_state_name = serializers.SerializerMethodField()

    is_receipt_overdue = serializers.SerializerMethodField()
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
            "payment_percent",
            "receipt_percent",
            "receipt_state",
            "receipt_state_name",
            "is_receipt_overdue",
            "receipt_overdue_days",
            "receipt_expected_days",
            "items",
        ]
        read_only_fields = ("created_by", "created_at", "updated_at")

    def _get_annotated_value(self, obj, attr_name):
        value = getattr(obj, attr_name, None)
        if value is not None:
            return value
        return None

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

    def get_remaining_amount(self, obj):
        return self.get_order_total_amount(obj) - self.get_paid_amount(obj)

    def get_payment_percent(self, obj):
        annotated = self._get_annotated_value(obj, "payment_percent")
        if annotated is not None:
            return annotated

        order_total_amount = self.get_order_total_amount(obj)
        paid_amount = self.get_paid_amount(obj)

        if order_total_amount <= 0:
            return 0

        percent = round((paid_amount / order_total_amount) * 100)
        return max(0, min(100, percent))

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

        percent = round((received_total_amount / order_total_amount) * 100)
        return max(0, min(100, percent))

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