from decimal import Decimal

from rest_framework import serializers

from orders.models import (
    ExternalOrder,
    ExternalReceiptDocument,
    ExternalReceiptItem,
)


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

        if receipt_document.completed:
            raise serializers.ValidationError(
                "Неможливо змінювати рядки приходу після завершення документа приходу."
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
    clear_image = serializers.BooleanField(write_only=True, required=False, default=False)
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
            "completed",
            "sent_to_warehouse",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "comment",
            "image",
            "clear_image",
            "items",
        ]
        read_only_fields = ("created_by", "created_at", "updated_at")

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
        order = attrs.get("order")
        completed = attrs.get("completed")
        sent_to_warehouse = attrs.get("sent_to_warehouse")

        if self.instance is not None:
            if order is None:
                order = self.instance.order
            if completed is None:
                completed = self.instance.completed
            if sent_to_warehouse is None:
                sent_to_warehouse = self.instance.sent_to_warehouse

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

        if sent_to_warehouse and not completed:
            raise serializers.ValidationError({
                "sent_to_warehouse": (
                    "Документ приходу можна передати на склад лише після його завершення."
                )
            })

        if self.instance is not None and self.instance.completed and completed is False:
            raise serializers.ValidationError({
                "completed": "Прапорець завершення документа приходу не можна скасувати."
            })

        if (
            self.instance is not None
            and self.instance.sent_to_warehouse
            and sent_to_warehouse is False
        ):
            raise serializers.ValidationError({
                "sent_to_warehouse": "Прапорець передачі документа на склад не можна скасувати."
            })

        return attrs