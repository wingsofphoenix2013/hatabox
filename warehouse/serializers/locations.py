from rest_framework import serializers

from ..models import WarehouseLocation


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