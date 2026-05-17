from decimal import Decimal

from django.db import models, transaction

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.viewsets import ModelViewSet

from orders.models import (
    ExternalOrder,
    ExternalOrderEvent,
    ExternalPaymentDocument,
)

from orders.serializers import ExternalPaymentDocumentSerializer

from .external_orders import try_complete_order

from orders.services.external_order_events import create_external_order_event

class ExternalPaymentDocumentViewSet(ModelViewSet):
    queryset = ExternalPaymentDocument.objects.select_related(
        "order",
        "order__vendor",
        "created_by",
    ).order_by("-created_at", "-id")
    serializer_class = ExternalPaymentDocumentSerializer
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

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(payment_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(order__order_no__icontains=search)
                | models.Q(order__vendor__code__icontains=search)
                | models.Q(order__vendor__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        payment_document = serializer.save(created_by=self.request.user)

        create_external_order_event(
            order=payment_document.order,
            event_type=ExternalOrderEvent.EventType.PAYMENT_DOCUMENT_CREATED,
            source=ExternalOrderEvent.Source.FINANCE,
            title="Створено платіжний документ",
            payload={
                "payment_document_id": payment_document.id,
                "payment_no": payment_document.payment_no,
                "status": payment_document.status,
                "payment_amount": str(payment_document.payment_amount),
            },
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        old_status = serializer.instance.status

        with transaction.atomic():
            payment_document = serializer.save()
            order = payment_document.order

            if old_status != payment_document.status:
                create_external_order_event(
                    order=order,
                    event_type=ExternalOrderEvent.EventType.PAYMENT_DOCUMENT_STATUS_CHANGED,
                    source=ExternalOrderEvent.Source.FINANCE,
                    title="Статус платіжного документа змінено",
                    payload={
                        "payment_document_id": payment_document.id,
                        "payment_no": payment_document.payment_no,
                        "from": old_status,
                        "to": payment_document.status,
                    },
                    created_by=self.request.user,
                )

            if (
                old_status == ExternalPaymentDocument.StatusChoices.DRAFT
                and payment_document.status in [
                    ExternalPaymentDocument.StatusChoices.APPROVED,
                    ExternalPaymentDocument.StatusChoices.PAID,
                ]
            ):
                items_total_amount = Decimal("0.00")
                for item in order.items.all():
                    items_total_amount += item.quantity * item.agreed_price

                order_total_amount = items_total_amount - order.discount_amount

                committed_total = Decimal("0.00")
                committed_payments = ExternalPaymentDocument.objects.filter(
                    order=order,
                    status__in=[
                        ExternalPaymentDocument.StatusChoices.APPROVED,
                        ExternalPaymentDocument.StatusChoices.PAID,
                    ],
                )

                for payment in committed_payments:
                    committed_total += payment.payment_amount

                remaining_amount = order_total_amount - committed_total

                if remaining_amount > 0:
                    existing_draft = ExternalPaymentDocument.objects.filter(
                        order=order,
                        status=ExternalPaymentDocument.StatusChoices.DRAFT,
                    ).exclude(id=payment_document.id)

                    if not existing_draft.exists():
                        ExternalPaymentDocument.objects.create(
                            payment_no=f"AUTO-{order.order_no}-{ExternalPaymentDocument.objects.filter(order=order).count() + 1}",
                            order=order,
                            status=ExternalPaymentDocument.StatusChoices.DRAFT,
                            payment_amount=remaining_amount,
                            created_by=self.request.user,
                            comment="Автоматично створено на залишок суми замовлення.",
                        )

            try_complete_order(order, created_by=self.request.user)
