from rest_framework import serializers
from .models import ExternalOrderStatus, ExternalOrderPaymentStatus, TaxType


class ExternalOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalOrderStatus
        fields = "__all__"


class ExternalOrderPaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalOrderPaymentStatus
        fields = "__all__"


class TaxTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxType
        fields = "__all__"