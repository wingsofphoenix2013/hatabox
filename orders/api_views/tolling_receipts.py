from django.db import IntegrityError, models, transaction
from django.db.models import Prefetch

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from orders.models import (
    TollingOrder,
    TollingOrderEvent,
    TollingReceiptDocument,
    TollingReceiptItem,
)

from orders.serializers import (
    TollingReceiptDocumentSerializer,
    TollingReceiptItemSerializer,
)

from .tolling_orders import (
    try_complete_tolling_order,
    generate_tolling_receipt_no,
    validate_tolling_receipt_before_completion,
    create_next_tolling_receipt_draft_from_remainders,
)

from orders.services.tolling_order_events import create_tolling_order_event

class TollingReceiptDocumentViewSet(ModelViewSet):
    queryset = TollingReceiptDocument.objects.select_related(
        "order",
        "order__organization",
        "created_by",
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=TollingReceiptItem.objects.select_related(
                "order_item",
                "order_item__order",
                "order_item__inv_item",
                "order_item__inv_item__unit",
            ),
        )
    ).order_by("-created_at", "-id")
    serializer_class = TollingReceiptDocumentSerializer
    permission_classes = [DjangoModelPermissions]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = self.queryset

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_id__in=order)

        organization = self.request.query_params.getlist("organization")
        if organization:
            queryset = queryset.filter(order__organization_id__in=organization)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(receipt_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(order__order_no__icontains=search)
                | models.Q(order__organization__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        order = serializer.validated_data["order"]

        for _ in range(5):
            try:
                with transaction.atomic():
                    receipt_no = generate_tolling_receipt_no(order)

                    receipt_document = serializer.save(
                        receipt_no=receipt_no,
                        created_by=self.request.user,
                    )

                    create_tolling_order_event(
                        order=receipt_document.order,
                        event_type=TollingOrderEvent.EventType.RECEIPT_DOCUMENT_CREATED,
                        source=TollingOrderEvent.Source.LOGISTICS,
                        title="Створено документ приходу",
                        payload={
                            "receipt_document_id": receipt_document.id,
                            "receipt_no": receipt_document.receipt_no,
                            "receipt_date": str(receipt_document.receipt_date),
                        },
                        created_by=self.request.user,
                    )

                    return receipt_document
            except IntegrityError:
                continue

        raise ValidationError(
            "Не вдалося згенерувати унікальний номер документа приходу. Спробуйте ще раз."
        )

    def perform_update(self, serializer):
        instance = serializer.instance

        if instance.sent_to_warehouse:
            allowed_fields = {"comment", "image", "clear_image"}
            changed_fields = set(serializer.validated_data.keys())

            if not changed_fields.issubset(allowed_fields):
                raise ValidationError(
                    "Після передачі на склад можна змінювати лише коментар або файл."
                )

        elif instance.completed:
            allowed_fields = {"sent_to_warehouse", "comment", "image", "clear_image"}
            changed_fields = set(serializer.validated_data.keys())

            if not changed_fields.issubset(allowed_fields):
                raise ValidationError(
                    "Після завершення можна змінювати лише передачу на склад, коментар або файл."
                )

        will_be_completed = (
            not instance.completed
            and serializer.validated_data.get("completed") is True
        )

        old_sent_to_warehouse = instance.sent_to_warehouse

        with transaction.atomic():
            if will_be_completed:
                validate_tolling_receipt_before_completion(instance)

            receipt_document = serializer.save()
            order = receipt_document.order

            if (
                not old_sent_to_warehouse
                and receipt_document.sent_to_warehouse
            ):
                create_tolling_order_event(
                    order=order,
                    event_type=TollingOrderEvent.EventType.RECEIPT_DOCUMENT_SENT_TO_WAREHOUSE,
                    source=TollingOrderEvent.Source.LOGISTICS,
                    title="Документ приходу передано на склад",
                    payload={
                        "receipt_document_id": receipt_document.id,
                        "receipt_no": receipt_document.receipt_no,
                    },
                    created_by=self.request.user,
                )

            if will_be_completed:
                create_tolling_order_event(
                    order=order,
                    event_type=TollingOrderEvent.EventType.RECEIPT_DOCUMENT_COMPLETED,
                    source=TollingOrderEvent.Source.LOGISTICS,
                    title="Документ приходу завершено",
                    payload={
                        "receipt_document_id": receipt_document.id,
                        "receipt_no": receipt_document.receipt_no,
                    },
                    created_by=self.request.user,
                )

                try_complete_tolling_order(
                    order,
                    created_by=self.request.user,
                )

                if order.status != TollingOrder.StatusChoices.COMPLETED:
                    existing_draft_receipt = TollingReceiptDocument.objects.filter(
                        order=order,
                        completed=False,
                    ).exclude(id=receipt_document.id).exists()

                    if existing_draft_receipt:
                        raise ValidationError(
                            "Для цього замовлення вже існує інший незавершений документ приходу."
                        )

                    create_next_tolling_receipt_draft_from_remainders(
                        order=order,
                        created_by=self.request.user,
                    )
            else:
                try_complete_tolling_order(
                    order,
                    created_by=self.request.user,
                )

class TollingReceiptItemViewSet(ModelViewSet):
    queryset = TollingReceiptItem.objects.select_related(
        "receipt_document",
        "receipt_document__order",
        "order_item",
        "order_item__order",
        "order_item__inv_item",
        "order_item__inv_item__unit",
    ).order_by("receipt_document__receipt_no", "id")
    serializer_class = TollingReceiptItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        receipt_document = self.request.query_params.getlist("receipt_document")
        if receipt_document:
            queryset = queryset.filter(receipt_document_id__in=receipt_document)

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_item__order_id__in=order)

        organization = self.request.query_params.getlist("organization")
        if organization:
            queryset = queryset.filter(order_item__order__organization_id__in=organization)

        order_item = self.request.query_params.getlist("order_item")
        if order_item:
            queryset = queryset.filter(order_item_id__in=order_item)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(receipt_document__receipt_no__icontains=search)
                | models.Q(order_item__order__order_no__icontains=search)
                | models.Q(order_item__inv_item__internal_code__icontains=search)
                | models.Q(order_item__inv_item__name__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            receipt_item = serializer.save()
            try_complete_tolling_order(
                receipt_item.order_item.order,
                created_by=self.request.user,
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            receipt_item = serializer.save()
            try_complete_tolling_order(
                receipt_item.order_item.order,
                created_by=self.request.user,
            )

    def perform_destroy(self, instance):
        if instance.receipt_document.completed:
            raise ValidationError(
                "Неможливо видаляти рядки приходу після завершення документа приходу."
            )

        if instance.order_item.order.status == TollingOrder.StatusChoices.COMPLETED:
            raise ValidationError(
                "Неможливо видаляти рядки приходу для завершеного замовлення."
            )

        order = instance.order_item.order

        with transaction.atomic():
            instance.delete()
            try_complete_tolling_order(
                order,
                created_by=self.request.user,
            )