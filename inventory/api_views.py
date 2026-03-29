from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import InvUnit, InvItemCategory, InvItem
from .serializers import InvUnitSerializer, InvItemCategorySerializer, InvItemSerializer


class InvUnitViewSet(ReadOnlyModelViewSet):
    queryset = InvUnit.objects.filter(is_active=True)
    serializer_class = InvUnitSerializer
    
class InvItemCategoryViewSet(ReadOnlyModelViewSet):
    queryset = InvItemCategory.objects.filter(is_active=True)
    serializer_class = InvItemCategorySerializer
    
class InvItemViewSet(ReadOnlyModelViewSet):
    queryset = InvItem.objects.filter(is_active=True)
    serializer_class = InvItemSerializer