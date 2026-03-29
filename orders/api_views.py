from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from .models import ExternalOrder, ExternalOrderItem
from .serializers import ExternalOrderSerializer, ExternalOrderItemSerializer


class ExternalOrderViewSet(ModelViewSet):
    queryset = ExternalOrder.objects.all()
    serializer_class = ExternalOrderSerializer
    permission_classes = [DjangoModelPermissions]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        
class ExternalOrderItemViewSet(ModelViewSet):
    queryset = ExternalOrderItem.objects.all()
    serializer_class = ExternalOrderItemSerializer
    permission_classes = [DjangoModelPermissions]