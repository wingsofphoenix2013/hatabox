from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from .models import Vendor
from .serializers import VendorSerializer


class VendorViewSet(ReadOnlyModelViewSet):
    queryset = Vendor.objects.filter(is_active=True)
    serializer_class = VendorSerializer
    permission_classes = [DjangoModelPermissions]