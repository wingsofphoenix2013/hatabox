from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import ExternalOrderStatus, ExternalOrderPaymentStatus
from .serializers import ExternalOrderStatusSerializer, ExternalOrderPaymentStatusSerializer


class ExternalOrderStatusViewSet(ReadOnlyModelViewSet):
    queryset = ExternalOrderStatus.objects.filter(is_active=True)
    serializer_class = ExternalOrderStatusSerializer
    
class ExternalOrderPaymentStatusViewSet(ReadOnlyModelViewSet):
    queryset = ExternalOrderPaymentStatus.objects.filter(is_active=True)
    serializer_class = ExternalOrderPaymentStatusSerializer