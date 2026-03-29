from rest_framework import serializers
from .models import ExternalOrder, ExternalOrderItem


class ExternalOrderItemSerializer(serializers.ModelSerializer):
    vendor_item_name = serializers.CharField(source="vendor_item.item.name", read_only=True)
    vendor_name = serializers.CharField(source="vendor_item.vendor.name", read_only=True)

    class Meta:
        model = ExternalOrderItem
        fields = "__all__"


# 👉 отдельный serializer для вложенного отображения
class ExternalOrderItemNestedSerializer(serializers.ModelSerializer):
    vendor_item_name = serializers.CharField(source="vendor_item.item.name", read_only=True)
    vendor_name = serializers.CharField(source="vendor_item.vendor.name", read_only=True)

    class Meta:
        model = ExternalOrderItem
        fields = "__all__"


class ExternalOrderSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    payment_status_name = serializers.CharField(source="payment_status.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    # 👉 ВАЖНО: вложенные строки заказа
    items = ExternalOrderItemNestedSerializer(many=True, read_only=True)

    class Meta:
        model = ExternalOrder
        fields = "__all__"
        read_only_fields = ("created_by", "created_at", "updated_at")