from decimal import Decimal

from rest_framework import serializers

from orders.models import (
    TollingOrder,
    TollingReceiptDocument,
    TollingReceiptItem,
)


class TollingReceiptItemSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(source="order_item.order.order_no", read_only=True)
    inv_item_name = serializers.CharField(source="order_item.inv_item.name", read_only=True)

    class Meta:
        model = TollingReceiptItem
        fields = [
            "id",
            "receipt_document",
            "order_item",
            "order_no",
            "inv_item_name",
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

        order = order_item.order

        if order.status == TollingOrder.StatusChoices.DRAFT:
            raise serializers.ValidationError(
                "Неможливо створювати прихід для замовлення у статусі 'Чернетка'."
            )

        if order.status == TollingOrder.StatusChoices.COMPLETED:
            raise serializers.ValidationError(
                "Неможливо змінювати рядки приходу для завершеного замовлення."
            )

        if receipt_document.completed:
            raise serializers.ValidationError(
                "Неможливо змінювати рядки після завершення документа приходу."
            )

        if receipt_document.order_id != order.id:
            raise serializers.ValidationError(
                "Рядок приходу повинен належати тому ж замовленню."
            )

        already_received = Decimal("0.000")
        for item in order_item.receipt_items.all():
            if self.instance and item.id == self.instance.id:
                continue
            already_received += item.received_quantity

        if already_received + received_quantity > order_item.quantity:
            raise serializers.ValidationError(
                "Отримана кількість перевищує замовлену."
            )

        return attrs


class TollingReceiptDocumentSerializer(serializers.ModelSerializer):
    clear_image = serializers.BooleanField(write_only=True, required=False, default=False)
    items = TollingReceiptItemSerializer(many=True, read_only=True)

    class Meta:
        model = TollingReceiptDocument
        fields = [
            "id",
            "receipt_no",
            "order",
            "receipt_date",
            "completed",
            "sent_to_warehouse",
            "created_by",
            "created_at",
            "updated_at",
            "comment",
            "image",
            "clear_image",
            "items",
        ]
        read_only_fields = ("receipt_no", "created_by", "created_at", "updated_at")

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

        if order.status == TollingOrder.StatusChoices.DRAFT:
            raise serializers.ValidationError(
                "Неможливо створювати документ приходу для чернетки."
            )

        if order.status == TollingOrder.StatusChoices.COMPLETED:
            raise serializers.ValidationError(
                "Неможливо змінювати документи для завершеного замовлення."
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