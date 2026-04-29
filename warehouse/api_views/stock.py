from rest_framework.exceptions import ValidationError
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from inventory.models import InvItem
from warehouse.services.stock_overview import build_stock_overview
from warehouse.services.stock_detail import build_stock_detail
from warehouse.serializers import (
    WarehouseStockOverviewRowSerializer,
    WarehouseStockDetailSerializer,
)

class WarehouseStockOverviewViewSet(ReadOnlyModelViewSet):
    queryset = InvItem.objects.all()
    serializer_class = WarehouseStockOverviewRowSerializer
    permission_classes = [DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        search = request.query_params.get("search")

        category_ids = request.query_params.getlist("category")
        location_ids = request.query_params.getlist("location")

        has_stock = request.query_params.get("has_stock")
        has_reserved = request.query_params.get("has_reserved")
        has_pending_intake = request.query_params.get("has_pending_intake")
        has_incoming = request.query_params.get("has_incoming")
        has_unconverted_pending_intake = request.query_params.get("has_unconverted_pending_intake")
        has_unconverted_incoming = request.query_params.get("has_unconverted_incoming")
        has_any_activity = request.query_params.get("has_any_activity")

        def parse_bool(value):
            if value is None:
                return None
            return value.lower() == "true"

        rows = build_stock_overview(
            search=search,
            category_ids=category_ids,
            location_ids=location_ids,
            has_stock=parse_bool(has_stock),
            has_reserved=parse_bool(has_reserved),
            has_pending_intake=parse_bool(has_pending_intake),
            has_incoming=parse_bool(has_incoming),
            has_unconverted_pending_intake=parse_bool(has_unconverted_pending_intake),
            has_unconverted_incoming=parse_bool(has_unconverted_incoming),
            has_any_activity=parse_bool(has_any_activity),
        )
        
        page = self.paginate_queryset(rows)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(rows, many=True)
        return Response(serializer.data)
        
class WarehouseStockDetailViewSet(ReadOnlyModelViewSet):
    queryset = InvItem.objects.all()
    serializer_class = WarehouseStockDetailSerializer
    permission_classes = [DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        raise ValidationError(
            "Цей endpoint підтримує лише detail-запит: /api/warehouse-stock-detail/{inventory_item_id}/"
        )

    def retrieve(self, request, *args, **kwargs):
        inventory_item_id = kwargs["pk"]
        data = build_stock_detail(inventory_item_id=inventory_item_id)
        serializer = self.get_serializer(data)
        return Response(serializer.data)