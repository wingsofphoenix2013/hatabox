from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import InvUnit, InvItemCategory
from .serializers import InvUnitSerializer, InvItemCategorySerializer


class InvUnitViewSet(ReadOnlyModelViewSet):
    queryset = InvUnit.objects.filter(is_active=True)
    serializer_class = InvUnitSerializer
    
class InvItemCategoryViewSet(ReadOnlyModelViewSet):
    queryset = InvItemCategory.objects.filter(is_active=True)
    serializer_class = InvItemCategorySerializer