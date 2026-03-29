from rest_framework import serializers
from .models import ExternalOrderStatus


class ExternalOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalOrderStatus
        fields = "__all__"