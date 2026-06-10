from rest_framework import serializers

from storage.models import (
    StoragePlace,
    StoragePlacePreferredItem,
)


class StoragePlacePreferredItemSerializer(serializers.ModelSerializer):
    inv_item_code = serializers.CharField(
        source="inv_item.internal_code",
        read_only=True,
    )
    inv_item_name = serializers.CharField(
        source="inv_item.name",
        read_only=True,
    )

    class Meta:
        model = StoragePlacePreferredItem
        fields = [
            "id",
            "inv_item",
            "inv_item_code",
            "inv_item_name",
        ]


class StoragePlaceSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(
        source="parent.code",
        read_only=True,
    )
    parent_address = serializers.CharField(
        source="parent.address",
        read_only=True,
    )

    preferred_items = StoragePlacePreferredItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = StoragePlace
        fields = [
            "id",
            "location",
            "parent",
            "parent_code",
            "parent_address",
            "place_type",
            "code",
            "address",
            "name",
            "comment",
            "is_active",
            "is_default",
            "preferred_items",
        ]
        read_only_fields = (
            "code",
            "address",
            "is_default",
        )