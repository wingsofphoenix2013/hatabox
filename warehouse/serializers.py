from rest_framework import serializers

from .models import WarehouseLocation, WarehouseStoragePlace


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


class WarehouseStoragePlaceSerializer(serializers.ModelSerializer):
    location_code = serializers.CharField(source="location.code", read_only=True)
    parent_code = serializers.CharField(source="parent.code", read_only=True)
    parent_display_name = serializers.CharField(source="parent.get_display_name", read_only=True)
    place_type_name = serializers.CharField(source="get_place_type_display", read_only=True)
    display_name = serializers.CharField(source="get_display_name", read_only=True)

    class Meta:
        model = WarehouseStoragePlace
        fields = [
            "id",
            "location",
            "location_code",
            "parent",
            "parent_code",
            "parent_display_name",
            "place_type",
            "place_type_name",
            "code",
            "name",
            "comment",
            "qr_code",
            "image",
            "is_active",
            "display_name",
        ]
        read_only_fields = ("code", "qr_code", "display_name")