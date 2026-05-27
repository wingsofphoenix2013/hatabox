from django.db import models, transaction

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet

from orders.models import (
    ExternalOrderEvent,
    ReclamationReturnDocument,
    ReclamationReturnItem,
    ReclamationReturnDocumentLibrary,
    ReclamationReturnDocumentLibraryItem,
)

from warehouse.models import (
    WarehouseUnit,
    WarehouseUnitEvent,
)

from orders.serializers import (
    ReclamationReturnDocumentSerializer,
    ReclamationReturnItemSerializer,
    ReclamationReturnDocumentLibrarySerializer,
    ReclamationReturnDocumentLibraryItemSerializer,
)

from orders.services.external_order_events import create_external_order_event


class ReclamationReturnDocumentViewSet(ModelViewSet):
    queryset = ReclamationReturnDocument.objects.select_related(
        "order",
        "order__vendor",
        "created_by",
    ).prefetch_related(
        "items",
    ).order_by("-created_at", "-id")

    serializer_class = ReclamationReturnDocumentSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_id__in=order)

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        reason = self.request.query_params.getlist("reason")
        if reason:
            queryset = queryset.filter(reason__in=reason)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(return_no__icontains=search)
                | models.Q(order__order_no__icontains=search)
                | models.Q(comment__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        reclamation_document = serializer.save(
            created_by=self.request.user,
        )

        order = reclamation_document.order

        if not order.has_reclamation:
            order.has_reclamation = True
            order.save(update_fields=["has_reclamation"])

    def perform_update(self, serializer):
        if serializer.instance.status in [
            ReclamationReturnDocument.StatusChoices.COMPLETED,
            ReclamationReturnDocument.StatusChoices.CANCELLED,
        ]:
            raise ValidationError(
                "Неможливо змінювати завершену або скасовану рекламацію."
            )

        old_status = serializer.instance.status

        with transaction.atomic():
            reclamation_document = serializer.save()

            if (
                old_status != ReclamationReturnDocument.StatusChoices.COMPLETED
                and reclamation_document.status == ReclamationReturnDocument.StatusChoices.COMPLETED
            ):
                items = list(
                    reclamation_document.items.select_related(
                        "warehouse_unit",
                    )
                )

                if not items:
                    raise ValidationError(
                        "Неможливо завершити рекламацію без складських одиниць."
                    )

                for item in items:
                    unit = item.warehouse_unit
                    from_location = unit.location
                    from_storage_place = unit.storage_place

                    unit.status = WarehouseUnit.Status.RETURNED
                    unit.location = None
                    unit.storage_place = None
                    unit.save()

                    WarehouseUnitEvent.objects.create(
                        operation_type=WarehouseUnitEvent.OperationType.RECLAMATION_RETURN,
                        source_unit=unit,
                        result_unit=unit,
                        quantity=item.quantity,
                        from_location=from_location,
                        from_storage_place=from_storage_place,
                        to_location=None,
                        to_storage_place=None,
                        created_by=self.request.user,
                    )

                create_external_order_event(
                    order=reclamation_document.order,
                    event_type=ExternalOrderEvent.EventType.RECLAMATION_RETURN_COMPLETED,
                    source=ExternalOrderEvent.Source.SYSTEM,
                    title="Завершено рекламацію",
                    message="Складські одиниці повернено постачальнику.",
                    payload={
                        "reclamation_return_document_id": reclamation_document.id,
                        "return_no": reclamation_document.return_no,
                    },
                    created_by=self.request.user,
                )


class ReclamationReturnItemViewSet(ModelViewSet):
    queryset = ReclamationReturnItem.objects.select_related(
        "return_document",
        "return_document__order",
        "warehouse_unit",
        "warehouse_unit__inventory_item",
    ).order_by("id")

    serializer_class = ReclamationReturnItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        return_document = self.request.query_params.getlist("return_document")
        if return_document:
            queryset = queryset.filter(
                return_document_id__in=return_document
            )

        warehouse_unit = self.request.query_params.getlist("warehouse_unit")
        if warehouse_unit:
            queryset = queryset.filter(
                warehouse_unit_id__in=warehouse_unit
            )

        return queryset


class ReclamationReturnDocumentLibraryViewSet(ModelViewSet):
    queryset = ReclamationReturnDocumentLibrary.objects.select_related(
        "return_document",
    ).prefetch_related(
        "items",
    )

    serializer_class = ReclamationReturnDocumentLibrarySerializer
    permission_classes = [DjangoModelPermissions]


class ReclamationReturnDocumentLibraryItemViewSet(ModelViewSet):
    queryset = ReclamationReturnDocumentLibraryItem.objects.select_related(
        "library",
        "library__return_document",
    ).order_by("id")

    serializer_class = ReclamationReturnDocumentLibraryItemSerializer
    permission_classes = [DjangoModelPermissions]