from rest_framework import serializers

from ..models import WarehouseStoragePlace


class WarehouseStoragePlaceSerializer(serializers.ModelSerializer):
    location_code = serializers.CharField(source="location.code", read_only=True)
    parent_code = serializers.CharField(source="parent.code", read_only=True)
    parent_display_name = serializers.CharField(source="parent.get_display_name", read_only=True)
    place_type_name = serializers.CharField(source="get_place_type_display", read_only=True)
    display_name = serializers.CharField(source="get_display_name", read_only=True)
    placement_display = serializers.SerializerMethodField()
    display_name_verbose = serializers.SerializerMethodField()

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
            "placement_display",
            "display_name_verbose",
            "name",
            "comment",
            "qr_code",
            "image",
            "is_active",
            "display_name",
        ]
        read_only_fields = ("code", "qr_code", "display_name")

    def get_placement_display(self, obj):
        if obj.parent is None:
            return "На локації"

        ancestors = []
        current = obj.parent

        while current is not None:
            ancestors.append(f"{current.get_place_type_display()} {current.code}")
            current = current.parent

        ancestors.reverse()
        return ", ".join(ancestors)
        
    def get_display_name_verbose(self, obj):
        return obj.get_display_name_verbose()
