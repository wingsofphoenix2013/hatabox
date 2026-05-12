from rest_framework.exceptions import ValidationError
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from inventory.models import InvItem

from warehouse.serializers import (
    WarehouseShortageDetailSerializer,
)
from warehouse.services.shortage_detail import (
    build_shortage_detail,
)


class WarehouseShortageDetailViewSet(ReadOnlyModelViewSet):
    queryset = InvItem.objects.all()
    serializer_class = WarehouseShortageDetailSerializer
    permission_classes = [DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        raise ValidationError(
            "Цей endpoint підтримує лише detail-запит: /api/warehouse-shortage-detail/{inv_item_id}/"
        )

    def retrieve(self, request, *args, **kwargs):
        inv_item_id = kwargs["pk"]

        data = build_shortage_detail(
            inv_item_id=inv_item_id,
        )

        if data is None:
            raise ValidationError(
                "Дефіцит для цієї номенклатури не знайдено."
            )

        serializer = self.get_serializer(data)

        return Response(serializer.data)