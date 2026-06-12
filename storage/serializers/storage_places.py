from rest_framework import serializers

from storage.models import (
    StoragePlace,
    StoragePlacePreferredItem,
)


class StoragePlacePreferredItemSerializer(serializers.ModelSerializer):
    def validate_inv_item(self, inv_item):
        if not inv_item.requires_storage_place:
            raise serializers.ValidationError(
                "Ця номенклатура не потребує стабільного місця зберігання."
            )

        existing = StoragePlacePreferredItem.objects.filter(
            inv_item=inv_item,
        ).first()

        if existing:
            raise serializers.ValidationError(
                f"Для цієї номенклатури вже призначено місце зберігання: {existing.storage_place.address}."
            )

        return inv_item

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
            "storage_place",
            "inv_item",
            "inv_item_code",
            "inv_item_name",
        ]


class StoragePlaceSummaryPreferredItemSerializer(serializers.ModelSerializer):
    internal_code = serializers.CharField(
        source="inv_item.internal_code",
        read_only=True,
    )
    name = serializers.CharField(
        source="inv_item.name",
        read_only=True,
    )

    class Meta:
        model = StoragePlacePreferredItem
        fields = [
            "id",
            "internal_code",
            "name",
        ]


class StoragePlaceParentOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True, allow_null=True)
    address = serializers.CharField(read_only=True, allow_null=True)
    address_verbose = serializers.CharField(read_only=True, allow_null=True)
    place_type = serializers.CharField(read_only=True, allow_null=True)
    place_type_name = serializers.CharField(read_only=True, allow_null=True)
    level = serializers.IntegerField(read_only=True)
    has_children = serializers.BooleanField(read_only=True)
    label = serializers.CharField(read_only=True)


class StoragePlaceSummarySerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(
        source="topology_level",
        read_only=True,
    )

    has_children = serializers.BooleanField(
        source="topology_has_children",
        read_only=True,
    )

    parent_id = serializers.IntegerField(
        read_only=True,
    )

    place_type_name = serializers.CharField(
        source="get_place_type_display",
        read_only=True,
    )

    location_id = serializers.IntegerField(
        source="root_location.id",
        read_only=True,
    )

    location_code = serializers.CharField(
        source="root_location.code",
        read_only=True,
    )

    location_name = serializers.CharField(
        source="root_location.name",
        read_only=True,
    )

    preferred_items_count = serializers.IntegerField(
        read_only=True,
    )

    preferred_items = StoragePlaceSummaryPreferredItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = StoragePlace
        fields = [
            "id",
            "location_id",
            "location_code",
            "location_name",
            "parent_id",
            "level",
            "has_children",
            "code",
            "address",
            "address_verbose",
            "name",
            "comment",
            "place_type",
            "place_type_name",
            "is_default",
            "preferred_items_count",
            "preferred_items",
        ]

class StoragePlaceDetailEventSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    event_type = serializers.CharField(read_only=True)
    event_type_name = serializers.CharField(read_only=True)
    payload = serializers.DictField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    comment = serializers.CharField(read_only=True)


class StoragePlaceDetailSerializer(serializers.Serializer):
    summary = serializers.DictField(read_only=True)
    preferred_items = StoragePlaceSummaryPreferredItemSerializer(
        many=True,
        read_only=True,
    )
    events = StoragePlaceDetailEventSerializer(
        many=True,
        read_only=True,
    )


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
            "address_verbose",
            "name",
            "comment",
            "is_active",
            "is_default",
            "preferred_items",
        ]
        read_only_fields = (
            "code",
            "address",
            "address_verbose",
            "is_default",
        )