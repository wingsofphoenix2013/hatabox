from rest_framework import serializers
from .models import (
    Brand,
    Country,
    ExternalOrderStatus,
    ExternalOrderPaymentStatus,
    TaxType,
)


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = "__all__"


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