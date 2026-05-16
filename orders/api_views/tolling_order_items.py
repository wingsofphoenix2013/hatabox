from django.db import models

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from orders.models import TollingOrder, TollingOrderItem

from orders.serializers import TollingOrderItemSerializer

class TollingOrderItemViewSet(ModelViewSet):
    queryset = TollingOrderItem.objects.select_related(
        "order",
        "order__organization",
        "inv_item",
        "inv_item__category",
        "inv_item__unit",
    ).order_by("order__order_no", "id")
    serializer_class = TollingOrderItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_id__in=order)

        organization = self.request.query_params.getlist("organization")
        if organization:
            queryset = queryset.filter(order__organization_id__in=organization)

        inv_item = self.request.query_params.getlist("inv_item")
        if inv_item:
            queryset = queryset.filter(inv_item_id__in=inv_item)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(order__order_no__icontains=search)
                | models.Q(inv_item__internal_code__icontains=search)
                | models.Q(inv_item__name__icontains=search)
            )

        return queryset

    def perform_destroy(self, instance):
        if instance.order.status != TollingOrder.StatusChoices.DRAFT:
            raise ValidationError(
                "Видалення рядків дозволене лише для замовлень у статусі 'Чернетка'."
            )

        instance.delete()
