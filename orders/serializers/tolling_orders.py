from datetime import date
from decimal import Decimal

from rest_framework import serializers

from orders.models import TollingOrder

from .tolling_order_items import TollingOrderItemSerializer


class TollingOrderRegisterLightSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_type = serializers.CharField(source="organization.type", read_only=True)
    organization_type_name = serializers.CharField(source="organization.get_type_display", read_only=True)

    is_overdue = serializers.SerializerMethodField()
    overdue_days = serializers.SerializerMethodField()

    class Meta:
        model = TollingOrder
        fields = [
            "id",
            "order_no",
            "organization",
            "organization_name",
            "organization_type",
            "organization_type_name",
            "status",
            "created_at",
            "comment",
            "is_overdue",
            "overdue_days",
        ]
        read_only_fields = fields

    def get_is_overdue(self, obj):
        return TollingOrderSerializer().get_is_overdue(obj)

    def get_overdue_days(self, obj):
        return TollingOrderSerializer().get_overdue_days(obj)


class TollingOrderSerializer(serializers.ModelSerializer):
    clear_image = serializers.BooleanField(write_only=True, required=False, default=False)

    organization_name = serializers.CharField(source="organization.name", read_only=True)

    items = TollingOrderItemSerializer(many=True, read_only=True)

    received_total_quantity = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    overdue_days = serializers.SerializerMethodField()
    expected_days = serializers.SerializerMethodField()

    class Meta:
        model = TollingOrder
        fields = [
            "id",
            "order_no",
            "organization",
            "organization_name",
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "comment",
            "image",
            "clear_image",
            "items",
            "received_total_quantity",
            "is_completed",
            "is_overdue",
            "overdue_days",
            "expected_days",
        ]
        read_only_fields = ("order_no", "created_by", "created_at", "updated_at")

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

    def get_received_total_quantity(self, obj):
        total = Decimal("0.000")
        for item in obj.items.all():
            for receipt_item in item.receipt_items.all():
                if receipt_item.receipt_document.completed:
                    total += receipt_item.received_quantity
        return str(total)

    def get_is_completed(self, obj):
        if obj.status == TollingOrder.StatusChoices.COMPLETED:
            return True
        return False

    def _get_tolling_overdue_data(self, obj):
        if obj.status == TollingOrder.StatusChoices.COMPLETED:
            return {
                "is_overdue": False,
                "overdue_days": None,
                "expected_days": None,
            }

        today = date.today()
        relevant_expected_delivery_date = None

        items = getattr(obj, "prefetched_items", None)
        if items is None:
            items = obj.items.all()

        for item in items:
            received_quantity = Decimal("0.000")

            receipt_items = getattr(item, "prefetched_receipt_items", None)
            if receipt_items is None:
                receipt_items = item.receipt_items.all()

            for receipt_item in receipt_items:
                if receipt_item.receipt_document.completed:
                    received_quantity += receipt_item.received_quantity

            if received_quantity < item.quantity and item.expected_delivery_date is not None:
                if (
                    relevant_expected_delivery_date is None
                    or item.expected_delivery_date < relevant_expected_delivery_date
                ):
                    relevant_expected_delivery_date = item.expected_delivery_date

        if relevant_expected_delivery_date is None:
            return {
                "is_overdue": False,
                "overdue_days": None,
                "expected_days": None,
            }

        if relevant_expected_delivery_date < today:
            return {
                "is_overdue": True,
                "overdue_days": (today - relevant_expected_delivery_date).days,
                "expected_days": None,
            }

        return {
            "is_overdue": False,
            "overdue_days": None,
            "expected_days": (relevant_expected_delivery_date - today).days,
        }

    def get_is_overdue(self, obj):
        return self._get_tolling_overdue_data(obj)["is_overdue"]

    def get_overdue_days(self, obj):
        return self._get_tolling_overdue_data(obj)["overdue_days"]

    def get_expected_days(self, obj):
        return self._get_tolling_overdue_data(obj)["expected_days"]

    def validate(self, attrs):
        status = attrs.get("status")

        if self.instance is None:
            if status is not None and status != TollingOrder.StatusChoices.DRAFT:
                raise serializers.ValidationError({
                    "status": "Нове давальницьке замовлення можна створити лише у статусі 'Чернетка'."
                })
            return attrs

        if self.instance.status == TollingOrder.StatusChoices.COMPLETED:
            raise serializers.ValidationError(
                "Завершене замовлення не можна змінювати."
            )

        if status is None:
            return attrs

        if (
            self.instance.status == TollingOrder.StatusChoices.DRAFT
            and status in [
                TollingOrder.StatusChoices.DRAFT,
                TollingOrder.StatusChoices.ACTIVE,
            ]
        ):
            return attrs

        if (
            self.instance.status == TollingOrder.StatusChoices.ACTIVE
            and status == TollingOrder.StatusChoices.ACTIVE
        ):
            return attrs

        raise serializers.ValidationError({
            "status": "Дозволено лише перехід 'Чернетка' → 'Активне'. Статус 'Виконано' встановлюється автоматично."
        })