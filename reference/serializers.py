from rest_framework import serializers
from .models import ExternalOrderStatus, ExternalOrderPaymentStatus


class ExternalOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalOrderStatus
        fields = "__all__"
        
class ExternalOrderPaymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalOrderPaymentStatus
        fields = "__all__"