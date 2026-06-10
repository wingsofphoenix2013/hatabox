from rest_framework import serializers

from storage.models import StorageLocation


class StorageLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageLocation
        fields = [
            "id",
            "code",
            "name",
            "address",
            "comment",
            "is_active",
        ]
        read_only_fields = (
            "code",
        )