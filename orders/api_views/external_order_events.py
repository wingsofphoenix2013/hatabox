from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from orders.models import ExternalOrderEvent
from orders.serializers import ExternalOrderEventSerializer


class ExternalOrderEventViewSet(ReadOnlyModelViewSet):
    queryset = ExternalOrderEvent.objects.select_related(
        "order",
        "created_by",
    ).order_by("-created_at", "-id")
    serializer_class = ExternalOrderEventSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_id__in=order)

        event_type = self.request.query_params.getlist("event_type")
        if event_type:
            queryset = queryset.filter(event_type__in=event_type)

        source = self.request.query_params.getlist("source")
        if source:
            queryset = queryset.filter(source__in=source)

        return queryset