from django.db import models

from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from .models import InvUnit, InvItemCategory, InvItem
from .serializers import InvUnitSerializer, InvItemCategorySerializer, InvItemSerializer


class InvUnitViewSet(ReadOnlyModelViewSet):
    queryset = InvUnit.objects.filter(is_active=True)
    serializer_class = InvUnitSerializer
    
class InvItemCategoryViewSet(ReadOnlyModelViewSet):
    queryset = InvItemCategory.objects.filter(is_active=True)
    serializer_class = InvItemCategorySerializer
    
class InvItemViewSet(ModelViewSet):
    queryset = InvItem.objects.filter(is_active=True)
    serializer_class = InvItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        category = self.request.query_params.getlist("category")
        if category:
            queryset = queryset.filter(category_id__in=category)
            
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(internal_code__icontains=search)
            )

        return queryset