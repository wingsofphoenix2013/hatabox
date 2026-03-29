from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import InvUnit
from .serializers import InvUnitSerializer


class InvUnitViewSet(ReadOnlyModelViewSet):
    queryset = InvUnit.objects.filter(is_active=True)
    serializer_class = InvUnitSerializer