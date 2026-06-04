from decimal import Decimal

from rest_framework import serializers

from orders.models import (
    ExternalOrder,
    ExternalPaymentDocument,
    ExternalRefundDocument,
)

PAYMENT_COMPLETION_TOLERANCE = Decimal("0.01")


class ExternalPaymentDocumentShortSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ExternalPaymentDocument
        fields = [
            "id",
            "payment_no",
            "status",
            "status_name",
            "payment_amount",
            "payment_date",
            "image",
        ]


class ExternalPaymentDocumentSerializer(serializers.ModelSerializer):
    clear_image = serializers.BooleanField(write_only=True, required=False, default=False)
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
            "image",
            "clear_image",
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
        if planned_total + payment_amount > order_total_amount + PAYMENT_COMPLETION_TOLERANCE:
            raise serializers.ValidationError(
                "Сума всіх платіжних документів не може перевищувати суму замовлення."
            )

        return attrs
        
class ExternalRefundDocumentSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(
        source="order.order_no",
        read_only=True,
    )
    order_vendor_id = serializers.IntegerField(
        source="order.vendor.id",
        read_only=True,
    )
    order_vendor_code = serializers.CharField(
        source="order.vendor.code",
        read_only=True,
    )
    order_vendor_name = serializers.CharField(
        source="order.vendor.name",
        read_only=True,
    )
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = ExternalRefundDocument
        fields = [
            "id",
            "refund_no",
            "order",
            "order_no",
            "order_vendor_id",
            "order_vendor_code",
            "order_vendor_name",
            "refund_amount",
            "refund_date",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "comment",
        ]
        read_only_fields = (
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        refund_amount = attrs.get("refund_amount")

        if self.instance is not None and refund_amount is None:
            refund_amount = self.instance.refund_amount

        if refund_amount is not None and refund_amount <= 0:
            raise serializers.ValidationError({
                "refund_amount": "Сума повернення повинна бути більше 0."
            })

        return attrs