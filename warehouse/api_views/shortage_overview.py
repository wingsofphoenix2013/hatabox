from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from warehouse.models import WarehouseSalesOrderShortage
from warehouse.serializers import (
    WarehouseShortageOverviewRowSerializer,
)
from warehouse.services.shortage_overview import (
    build_shortage_overview,
)


class WarehouseShortageOverviewViewSet(ReadOnlyModelViewSet):
    queryset = WarehouseSalesOrderShortage.objects.none()
    serializer_class = WarehouseShortageOverviewRowSerializer
    permission_classes = [DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        rows = build_shortage_overview()

        page = self.paginate_queryset(rows)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(rows, many=True)

        return Response(serializer.data)