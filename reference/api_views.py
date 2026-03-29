from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import ExternalOrderStatus
from .serializers import ExternalOrderStatusSerializer


class ExternalOrderStatusViewSet(ReadOnlyModelViewSet):
    queryset = ExternalOrderStatus.objects.filter(is_active=True)
    serializer_class = ExternalOrderStatusSerializer