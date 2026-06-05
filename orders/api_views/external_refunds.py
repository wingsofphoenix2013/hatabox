from django.db import models, transaction

from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet

from orders.models import (
    ExternalOrderEvent,
    ExternalRefundDocument,
)
from orders.serializers import ExternalRefundDocumentSerializer
from orders.services.external_order_events import create_external_order_event
from orders.services.external_order_status import (
    recalculate_external_order_status_after_reclamation_or_refund,
)

from warehouse.tasks import recalculate_warehouse_shortages_task


class ExternalRefundDocumentViewSet(ModelViewSet):
    queryset = ExternalRefundDocument.objects.select_related(
        "order",
        "order__vendor",
        "created_by",
    ).order_by("-created_at", "-id")

    serializer_class = ExternalRefundDocumentSerializer
    permission_classes = [DjangoModelPermissions]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = self.queryset

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_id__in=order)

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(order__vendor_id__in=vendor)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(refund_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(order__order_no__icontains=search)
                | models.Q(order__vendor__code__icontains=search)
                | models.Q(order__vendor__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset

    def update(self, request, *args, **kwargs):
        raise ValidationError(
            "Документ повернення коштів не можна змінювати після створення."
        )

    def partial_update(self, request, *args, **kwargs):
        raise ValidationError(
            "Документ повернення коштів не можна змінювати після створення."
        )

    def destroy(self, request, *args, **kwargs):
        raise ValidationError(
            "Документ повернення коштів не можна видаляти після створення."
        )

    def perform_create(self, serializer):
        refund_document = serializer.save(
            created_by=self.request.user,
        )

        create_external_order_event(
            order=refund_document.order,
            event_type=ExternalOrderEvent.EventType.REFUND_DOCUMENT_CREATED,
            source=ExternalOrderEvent.Source.FINANCE,
            title="Отримано повернення коштів",
            payload={
                "refund_document_id": refund_document.id,
                "refund_no": refund_document.refund_no,
                "refund_amount": str(refund_document.refund_amount),
                "refund_date": str(refund_document.refund_date),
            },
            created_by=self.request.user,
        )

        recalculate_external_order_status_after_reclamation_or_refund(
            order=refund_document.order,
            created_by=self.request.user,
        )

        affected_inv_item_ids = list({
            item.vendor_item.item_id
            for item in refund_document.order.items.select_related(
                "vendor_item",
                "vendor_item__item",
            )
        })

        if affected_inv_item_ids:
            transaction.on_commit(
                lambda: recalculate_warehouse_shortages_task.delay(
                    inv_item_ids=affected_inv_item_ids,
                )
            )