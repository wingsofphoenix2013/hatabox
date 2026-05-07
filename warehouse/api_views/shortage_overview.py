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
        search = request.query_params.get("search")

        fulfillment_mode = request.query_params.get("fulfillment_mode")

        is_required_for_start = request.query_params.get(
            "is_required_for_start"
        )

        if is_required_for_start is not None:
            is_required_for_start = (
                is_required_for_start.lower() == "true"
            )

        rows = build_shortage_overview(
            search=search,
            fulfillment_mode=fulfillment_mode,
            is_required_for_start=is_required_for_start,
        )

        page = self.paginate_queryset(rows)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(rows, many=True)

        return Response(serializer.data)