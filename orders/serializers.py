from rest_framework import serializers
from .models import ExternalOrder


class ExternalOrderSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    payment_status_name = serializers.CharField(source="payment_status.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = ExternalOrder
        fields = "__all__"