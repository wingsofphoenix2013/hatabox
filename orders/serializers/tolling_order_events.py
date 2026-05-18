from rest_framework import serializers

from orders.models import TollingOrderEvent


class TollingOrderEventSerializer(serializers.ModelSerializer):
    event_type_name = serializers.CharField(source="get_event_type_display", read_only=True)
    source_name = serializers.CharField(source="get_source_display", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = TollingOrderEvent
        fields = [
            "id",
            "order",
            "event_type",
            "event_type_name",
            "source",
            "source_name",
            "title",
            "message",
            "payload",
            "created_by",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = fields