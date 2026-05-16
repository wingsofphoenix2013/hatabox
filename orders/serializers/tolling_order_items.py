from decimal import Decimal

from rest_framework import serializers

from orders.models import (
    TollingOrder,
    TollingOrderItem,
)


class TollingOrderItemSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(source="order.order_no", read_only=True)

    inv_item_name = serializers.CharField(source="inv_item.name", read_only=True)
    inv_item_internal_code = serializers.CharField(source="inv_item.internal_code", read_only=True)
    inv_item_unit_name = serializers.CharField(source="inv_item.unit.name", read_only=True)
    inv_item_unit_symbol = serializers.CharField(source="inv_item.unit.symbol", read_only=True)

    received_quantity = serializers.SerializerMethodField()
    remaining_quantity = serializers.SerializerMethodField()

    class Meta:
        model = TollingOrderItem
        fields = [
            "id",
            "order",
            "order_no",
            "inv_item",
            "inv_item_internal_code",
            "inv_item_name",
            "inv_item_unit_name",
            "inv_item_unit_symbol",
            "quantity",
            "requires_unit_conversion",
            "expected_delivery_date",
            "received_quantity",
            "remaining_quantity",
        ]

    def get_received_quantity(self, obj):
        total = Decimal("0.000")
        for receipt_item in obj.receipt_items.all():
            if receipt_item.receipt_document.completed:
                total += receipt_item.received_quantity
        return str(total)

    def get_remaining_quantity(self, obj):
        remaining = obj.quantity - Decimal(self.get_received_quantity(obj))
        return str(remaining)

    def validate(self, attrs):
        order = attrs.get("order")
        inv_item = attrs.get("inv_item")
        requires_unit_conversion = attrs.get("requires_unit_conversion")

        if self.instance is not None:
            order = self.instance.order

            if inv_item is None:
                inv_item = self.instance.inv_item

            if requires_unit_conversion is None:
                requires_unit_conversion = self.instance.requires_unit_conversion

        if order is None:
            return attrs

        if order.status != TollingOrder.StatusChoices.DRAFT:
            if (
                self.instance is not None
                and order.status == TollingOrder.StatusChoices.ACTIVE
                and set(attrs.keys()) == {"expected_delivery_date"}
            ):
                return attrs

            raise serializers.ValidationError(
                "Після активації замовлення можна змінювати лише очікувану дату поставки."
            )

        if requires_unit_conversion:
            raise serializers.ValidationError({
                "requires_unit_conversion": (
                    "Для давальницьких замовлень конвертація одиниць не використовується."
                )
            })

        if inv_item is not None:
            duplicate_qs = TollingOrderItem.objects.filter(
                order=order,
                inv_item=inv_item,
            )

            if self.instance is not None:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)

            if duplicate_qs.exists():
                raise serializers.ValidationError({
                    "inv_item": "Ця номенклатурна позиція вже існує в замовленні."
                })

        return attrs