from rest_framework import serializers
from .models import InvUnit


class InvUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvUnit
        fields = "__all__"