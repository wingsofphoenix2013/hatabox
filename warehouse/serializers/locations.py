from rest_framework import serializers

from ..models import WarehouseLocation
from .storage_places import WarehouseStoragePlaceSerializer


class WarehouseLocationDirectStockRowSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)
    inventory_item_unit_symbol = serializers.CharField(read_only=True)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )


class WarehouseLocationDetailSerializer(serializers.Serializer):
    location = serializers.DictField(read_only=True)
    storage_places = WarehouseStoragePlaceSerializer(
        many=True,
        read_only=True,
    )
    direct_stock = WarehouseLocationDirectStockRowSerializer(
        many=True,
        read_only=True,
    )


class WarehouseLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseLocation
        fields = [
            "id",
            "code",
            "name",
            "address",
            "comment",
            "is_active",
        ]
        read_only_fields = ("code",)