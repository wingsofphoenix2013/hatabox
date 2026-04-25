from rest_framework import serializers

from inventory.models import InvItem
from ..models import WarehouseLocation, WarehouseStoragePlace


class WarehouseMoveSerializer(serializers.Serializer):
    inventory_item = serializers.PrimaryKeyRelatedField(
        queryset=InvItem.objects.all()
    )
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    target_location = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseLocation.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    target_storage_place = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseStoragePlace.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        target_location = attrs.get("target_location")
        target_storage_place = attrs.get("target_storage_place")

        if (target_location is None) == (target_storage_place is None):
            raise serializers.ValidationError(
                "Потрібно вказати або target_location, або target_storage_place, але не обидва одночасно."
            )

        return attrs


class WarehouseBulkMoveSerializer(serializers.Serializer):
    unit_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    target_location = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseLocation.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    target_storage_place = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseStoragePlace.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        target_location = attrs.get("target_location")
        target_storage_place = attrs.get("target_storage_place")

        if (target_location is None) == (target_storage_place is None):
            raise serializers.ValidationError(
                "Потрібно вказати або target_location, або target_storage_place, але не обидва одночасно."
            )

        return attrs
