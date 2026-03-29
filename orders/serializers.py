from rest_framework import serializers
from .models import ExternalOrder


class ExternalOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalOrder
        fields = "__all__"