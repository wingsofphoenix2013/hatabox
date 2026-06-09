import logging

from django.db import models, transaction

from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from orders.models import (
    ExternalOrder,
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
from warehouse.tasks import recalculate_warehouse_shortages_task

from orders.serializers import (
    ReclamationReturnDocumentSerializer,
    ReclamationReturnItemSerializer,
    ReclamationReturnDocumentLibrarySerializer,
    ReclamationReturnDocumentLibraryItemSerializer,
    CreateReclamationReturnDocumentSerializer,
    ReclamationReturnAvailabilityItemSerializer,
)

from orders.services.reclamation_returns import (
    create_reclamation_return_draft_from_cart,
    get_reclamation_return_availability,
)

from orders.services.external_order_status import (
    recalculate_external_order_status_after_reclamation_or_refund,
)

from orders.services.external_order_events import create_external_order_event

logger = logging.getLogger(__name__)


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

        ReclamationReturnDocumentLibrary.objects.get_or_create(
            return_document=reclamation_document,
        )

    @action(detail=False, methods=["post"], url_path="create-from-cart")
    def create_from_cart(self, request):
        serializer = CreateReclamationReturnDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reclamation_document = create_reclamation_return_draft_from_cart(
                order=serializer.validated_data["order"],
                reason=serializer.validated_data["reason"],
                return_date=serializer.validated_data["return_date"],
                comment=serializer.validated_data.get("comment", ""),
                items=serializer.validated_data["items"],
                created_by=request.user,
            )
        except Exception:
            logger.exception("Reclamation return create-from-cart failed")
            raise

        ReclamationReturnDocumentLibrary.objects.get_or_create(
            return_document=reclamation_document,
        )

        response_serializer = self.get_serializer(reclamation_document)
        return Response(response_serializer.data)

    @action(detail=True, methods=["post"], url_path="execute")
    def execute(self, request, pk=None):
        reclamation_document = self.get_object()

        serializer = self.get_serializer(
            reclamation_document,
            data={
                "status": ReclamationReturnDocument.StatusChoices.COMPLETED,
            },
            partial=True,
            context={
                **self.get_serializer_context(),
                "allow_status_change": True,
            },
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        reclamation_document.refresh_from_db()
        response_serializer = self.get_serializer(reclamation_document)
        return Response(response_serializer.data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        reclamation_document = self.get_object()

        if reclamation_document.status != ReclamationReturnDocument.StatusChoices.DRAFT:
            raise ValidationError(
                "Скасувати можна лише рекламацію у статусі 'Чернетка'."
            )

        serializer = self.get_serializer(
            reclamation_document,
            data={
                "status": ReclamationReturnDocument.StatusChoices.CANCELLED,
            },
            partial=True,
            context={
                **self.get_serializer_context(),
                "allow_status_change": True,
            },
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        reclamation_document.refresh_from_db()
        response_serializer = self.get_serializer(reclamation_document)
        return Response(response_serializer.data)

    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        order_id = request.query_params.get("order")

        if not order_id:
            raise ValidationError({
                "order": "Потрібно вказати замовлення."
            })

        try:
            order = ExternalOrder.objects.get(id=order_id)
        except ExternalOrder.DoesNotExist:
            raise ValidationError({
                "order": "Замовлення не знайдено."
            })

        data = get_reclamation_return_availability(
            order=order,
        )

        serializer = ReclamationReturnAvailabilityItemSerializer(data, many=True)
        return Response(serializer.data)

    def perform_update(self, serializer):
        try:
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

                affected_inv_item_ids = set()

                if (
                    old_status != ReclamationReturnDocument.StatusChoices.CANCELLED
                    and reclamation_document.status == ReclamationReturnDocument.StatusChoices.CANCELLED
                ):
                    items = list(
                        reclamation_document.items.select_related(
                            "warehouse_unit",
                            "source_location",
                            "source_storage_place",
                        )
                    )

                    for item in items:
                        unit = item.warehouse_unit

                        if unit.status != WarehouseUnit.Status.BLOCKED:
                            raise ValidationError(
                                "Усі складські одиниці рекламації повинні бути заблоковані перед скасуванням."
                            )

                        unit.status = WarehouseUnit.Status.ON_STOCK
                        unit.location = item.source_location if item.source_storage_place is None else None
                        unit.storage_place = item.source_storage_place
                        unit.save()

                        affected_inv_item_ids.add(unit.inventory_item_id)

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

                        if unit.status != WarehouseUnit.Status.BLOCKED:
                            raise ValidationError(
                                "Усі складські одиниці рекламації повинні бути заблоковані перед завершенням."
                            )

                        unit.status = WarehouseUnit.Status.RETURNED
                        unit.location = None
                        unit.storage_place = None
                        unit.save()

                        WarehouseUnitEvent.objects.create(
                            operation_type=WarehouseUnitEvent.OperationType.RECLAMATION_RETURN,
                            source_unit=unit,
                            result_unit=unit,
                            quantity=item.quantity,
                            from_location=item.source_location if item.source_storage_place is None else None,
                            from_storage_place=item.source_storage_place,
                            to_location=None,
                            to_storage_place=None,
                            created_by=self.request.user,
                        )

                        affected_inv_item_ids.add(unit.inventory_item_id)

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

                    recalculate_external_order_status_after_reclamation_or_refund(
                        order=reclamation_document.order,
                        created_by=self.request.user,
                    )

                if affected_inv_item_ids:
                    recalculate_warehouse_shortages_task.delay(
                        inv_item_ids=list(affected_inv_item_ids),
                    )

        except Exception:
            logger.exception("Reclamation return update failed")
            raise

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
    parser_classes = [MultiPartParser, FormParser]