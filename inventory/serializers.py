from rest_framework import serializers
from .models import InvUnit, InvItemCategory


class InvUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvUnit
        fields = "__all__"


class InvItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvItemCategory
        fields = "__all__"