from rest_framework import serializers
from .models import InvUnit, InvItemCategory, InvItem


class InvUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvUnit
        fields = "__all__"


class InvItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvItemCategory
        fields = "__all__"


class InvItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    unit_symbol = serializers.CharField(source="unit.symbol", read_only=True)

    class Meta:
        model = InvItem
        fields = "__all__"