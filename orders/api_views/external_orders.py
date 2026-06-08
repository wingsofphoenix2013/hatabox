from datetime import date
from decimal import Decimal

from django.db import models, transaction
from django.db.models import (
    BooleanField,
    Case,
    DateField,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Cast, Coalesce, Least, Round

from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from orders.models import (
    ExternalOrder,
    ExternalOrderEvent,
    ExternalOrderItem,
    ExternalPaymentDocument,
    ExternalRefundDocument,
    ExternalReceiptDocument,
    ExternalReceiptItem,
    ReclamationReturnDocument,
    ReclamationReturnItem,
)

from orders.serializers import (
    ExternalOrderSerializer,
    ExternalOrderRegistrySerializer,
    ExternalOrderRegisterLightSerializer,
)

from orders.services.external_order_events import create_external_order_event
from orders.services.warehouse_costs import recalculate_order_item_warehouse_cost

from warehouse.tasks import (
    recalculate_warehouse_shortages_task,
)


VAT_RATE = Decimal("0.20")
VAT_DIVISOR = Decimal("1.20")
PAYMENT_COMPLETION_TOLERANCE = Decimal("0.01")

def recalculate_order_vat_amount(order):
    vat_amount = Decimal("0.0000")

    if not order.vendor.vat:
        order.vat_amount = vat_amount
        order.save(update_fields=["vat_amount"])
        return

    for item in order.items.all():
        line_total = item.quantity * item.agreed_price
        line_vat = line_total * VAT_RATE / VAT_DIVISOR
        vat_amount += line_vat

    order.vat_amount = vat_amount.quantize(Decimal("0.0001"))
    order.save(update_fields=["vat_amount"])


def try_complete_order(order, created_by=None):
    items_total_amount = Decimal("0.00")
    for item in order.items.all():
        items_total_amount += item.quantity * item.agreed_price

    order_total_amount = items_total_amount - order.discount_amount

    paid_amount = Decimal("0.00")
    for payment in order.payment_documents.all():
        if payment.status == ExternalPaymentDocument.StatusChoices.PAID:
            paid_amount += payment.payment_amount

    received_total_amount = Decimal("0.00")
    for item in order.items.all():
        received_quantity = Decimal("0.000")
        for receipt_item in item.receipt_items.all():
            if receipt_item.receipt_document.completed:
                received_quantity += receipt_item.received_quantity

        capped_received_quantity = min(received_quantity, item.quantity)
        received_total_amount += capped_received_quantity * item.agreed_price

    payment_percent = 0
    receipt_percent = 0

    if order_total_amount > 0:
        if paid_amount + PAYMENT_COMPLETION_TOLERANCE >= order_total_amount:
            payment_percent = 100
        else:
            payment_percent = round((paid_amount / order_total_amount) * 100)
            payment_percent = max(0, min(99, payment_percent))

        if received_total_amount >= order_total_amount:
            receipt_percent = 100
        else:
            receipt_percent = round((received_total_amount / order_total_amount) * 100)
            receipt_percent = max(0, min(99, receipt_percent))

    if (
        payment_percent == 100
        and receipt_percent == 100
        and order.status != ExternalOrder.StatusChoices.COMPLETED
    ):
        old_status = order.status

        order.status = ExternalOrder.StatusChoices.COMPLETED
        order.save(update_fields=["status"])

        create_external_order_event(
            order=order,
            event_type=ExternalOrderEvent.EventType.ORDER_STATUS_CHANGED,
            source=ExternalOrderEvent.Source.SYSTEM,
            title="Замовлення автоматично завершено",
            message="Замовлення автоматично переведено у статус 'Виконано'.",
            payload={
                "from": old_status,
                "to": order.status,
                "reason": "auto_completion",
            },
            created_by=created_by,
        )

        for item in order.items.select_related(
            "order",
            "order__vendor",
            "vendor_item",
            "vendor_item__item",
        ):
            recalculate_order_item_warehouse_cost(item)
        

class ExternalOrderRegisterLightViewSet(ModelViewSet):
    queryset = ExternalOrder.objects.select_related(
        "vendor",
    ).order_by("-created_at", "-id")
    serializer_class = ExternalOrderRegisterLightSerializer
    permission_classes = [DjangoModelPermissions]

    def _with_registry_annotations(self, queryset):
        return ExternalOrderViewSet()._with_registry_annotations(queryset)

    def get_queryset(self):
        queryset = self._with_registry_annotations(self.queryset)

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        payment_ranges = self.request.query_params.getlist("payment_range")
        if payment_ranges:
            payment_q = Q()
            valid_payment_filter = False

            for value in payment_ranges:
                if value == "0":
                    payment_q |= Q(payment_percent=0)
                    valid_payment_filter = True
                elif value == "1-49":
                    payment_q |= Q(payment_percent__gte=1, payment_percent__lte=49)
                    valid_payment_filter = True
                elif value == "50-99":
                    payment_q |= Q(payment_percent__gte=50, payment_percent__lte=99)
                    valid_payment_filter = True
                elif value == "100":
                    payment_q |= Q(payment_percent=100)
                    valid_payment_filter = True

            if valid_payment_filter:
                queryset = queryset.filter(payment_q)

        receipt_ranges = self.request.query_params.getlist("receipt_range")
        if receipt_ranges:
            receipt_q = Q()
            valid_receipt_filter = False

            for value in receipt_ranges:
                if value == "overdue":
                    receipt_q |= Q(is_receipt_overdue=True)
                    valid_receipt_filter = True
                elif value == "0":
                    receipt_q |= Q(receipt_percent=0)
                    valid_receipt_filter = True
                elif value == "1-49":
                    receipt_q |= Q(receipt_percent__gte=1, receipt_percent__lte=49)
                    valid_receipt_filter = True
                elif value == "50-99":
                    receipt_q |= Q(receipt_percent__gte=50, receipt_percent__lte=99)
                    valid_receipt_filter = True
                elif value == "100":
                    receipt_q |= Q(receipt_percent=100)
                    valid_receipt_filter = True

            if valid_receipt_filter:
                queryset = queryset.filter(receipt_q)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(vendor__name__icontains=search)
            )

        ordering = self.request.query_params.get("ordering")
        allowed_ordering = {
            "order_total_amount",
            "-order_total_amount",
            "payment_percent",
            "-payment_percent",
            "receipt_percent",
            "-receipt_percent",
        }

        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering, "-id")

        return queryset


class ExternalOrderRegistryViewSet(ModelViewSet):
    queryset = ExternalOrder.objects.select_related(
        "vendor",
    ).order_by("-created_at", "-id")
    serializer_class = ExternalOrderRegistrySerializer
    permission_classes = [DjangoModelPermissions]

    def _with_registry_annotations(self, queryset):
        return ExternalOrderViewSet()._with_registry_annotations(queryset)

    def get_queryset(self):
        queryset = self._with_registry_annotations(self.queryset)

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(vendor_id__in=vendor)

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        created_by = self.request.query_params.getlist("created_by")
        if created_by:
            queryset = queryset.filter(created_by_id__in=created_by)

        payment_ranges = self.request.query_params.getlist("payment_range")
        if payment_ranges:
            payment_q = Q()
            valid_payment_filter = False

            for value in payment_ranges:
                if value == "0":
                    payment_q |= Q(payment_percent=0)
                    valid_payment_filter = True
                elif value == "1-49":
                    payment_q |= Q(payment_percent__gte=1, payment_percent__lte=49)
                    valid_payment_filter = True
                elif value == "50-99":
                    payment_q |= Q(payment_percent__gte=50, payment_percent__lte=99)
                    valid_payment_filter = True
                elif value == "100":
                    payment_q |= Q(payment_percent=100)
                    valid_payment_filter = True

            if valid_payment_filter:
                queryset = queryset.filter(payment_q)

        receipt_ranges = self.request.query_params.getlist("receipt_range")
        if receipt_ranges:
            receipt_q = Q()
            valid_receipt_filter = False

            for value in receipt_ranges:
                if value == "overdue":
                    receipt_q |= Q(is_receipt_overdue=True)
                    valid_receipt_filter = True
                elif value == "0":
                    receipt_q |= Q(receipt_percent=0)
                    valid_receipt_filter = True
                elif value == "1-49":
                    receipt_q |= Q(receipt_percent__gte=1, receipt_percent__lte=49)
                    valid_receipt_filter = True
                elif value == "50-99":
                    receipt_q |= Q(receipt_percent__gte=50, receipt_percent__lte=99)
                    valid_receipt_filter = True
                elif value == "100":
                    receipt_q |= Q(receipt_percent=100)
                    valid_receipt_filter = True

            if valid_receipt_filter:
                queryset = queryset.filter(receipt_q)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(order_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(vendor__code__icontains=search)
                | models.Q(vendor__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        ordering = self.request.query_params.get("ordering")
        allowed_ordering = {
            "order_total_amount",
            "-order_total_amount",
            "payment_percent",
            "-payment_percent",
            "receipt_percent",
            "-receipt_percent",
        }

        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering, "-id")

        return queryset


class ExternalOrderViewSet(ModelViewSet):
    queryset = ExternalOrder.objects.select_related(
        "vendor",
        "created_by",
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=ExternalOrderItem.objects.select_related(
                "vendor_item",
                "vendor_item__vendor",
                "vendor_item__item",
                "vendor_item__item__category",
                "vendor_item__item__unit",
                "vendor_item__brand",
                "vendor_item__country_of_origin",
            ).prefetch_related(
                Prefetch(
                    "receipt_items",
                    queryset=ExternalReceiptItem.objects.select_related("receipt_document"),
                    to_attr="prefetched_receipt_items",
                )
            ),
            to_attr="prefetched_items",
        ),
        Prefetch(
            "payment_documents",
            queryset=ExternalPaymentDocument.objects.select_related("created_by"),
            to_attr="prefetched_payment_documents",
        ),
        Prefetch(
            "receipt_documents",
            queryset=ExternalReceiptDocument.objects.only(
                "id",
                "order_id",
                "completed",
                "sent_to_warehouse",
            ),
            to_attr="prefetched_receipt_documents",
        ),
        Prefetch(
            "refund_documents",
            queryset=ExternalRefundDocument.objects.select_related(
                "created_by",
            ),
            to_attr="prefetched_refund_documents",
        ),
        Prefetch(
            "reclamation_returns",
            queryset=ReclamationReturnDocument.objects.prefetch_related(
                Prefetch(
                    "items",
                    queryset=ReclamationReturnItem.objects.select_related(
                        "order_item",
                    ),
                    to_attr="prefetched_items",
                )
            ),
            to_attr="prefetched_reclamation_returns",
        ),
    ).order_by("-created_at", "-id")
    serializer_class = ExternalOrderSerializer
    permission_classes = [DjangoModelPermissions]
    parser_classes = [MultiPartParser, FormParser]

    def _with_registry_annotations(self, queryset):
        today = date.today()

        paid_amount_subquery = (
            ExternalPaymentDocument.objects.filter(
                order_id=OuterRef("pk"),
                status=ExternalPaymentDocument.StatusChoices.PAID,
            )
            .values("order_id")
            .annotate(total=Sum("payment_amount"))
            .values("total")[:1]
        )

        order_items_base = ExternalOrderItem.objects.filter(order_id=OuterRef("pk")).annotate(
            receipt_quantity_total=Coalesce(
                Subquery(
                    ExternalReceiptItem.objects.filter(
                        order_item_id=OuterRef("pk"),
                        receipt_document__completed=True,
                    )
                    .values("order_item_id")
                    .annotate(total=Sum("received_quantity"))
                    .values("total")[:1]
                ),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=3),
            ),
            ordered_line_amount=ExpressionWrapper(
                F("quantity") * F("agreed_price"),
                output_field=DecimalField(max_digits=18, decimal_places=4),
            ),
            received_quantity_capped=Case(
                When(receipt_quantity_total__gt=F("quantity"), then=F("quantity")),
                default=F("receipt_quantity_total"),
                output_field=DecimalField(max_digits=12, decimal_places=3),
            ),
            received_line_amount=ExpressionWrapper(
                F("received_quantity_capped") * F("agreed_price"),
                output_field=DecimalField(max_digits=18, decimal_places=4),
            ),
        )

        items_total_amount_subquery = (
            order_items_base.values("order_id")
            .annotate(total=Sum("ordered_line_amount"))
            .values("total")[:1]
        )

        received_total_amount_subquery = (
            order_items_base.values("order_id")
            .annotate(total=Sum("received_line_amount"))
            .values("total")[:1]
        )

        expected_delivery_date_min_subquery = (
            order_items_base.filter(
                expected_delivery_date__isnull=False,
                receipt_quantity_total__lt=F("quantity"),
            )
            .order_by("expected_delivery_date")
            .values("expected_delivery_date")[:1]
        )

        queryset = queryset.annotate(
            items_total_amount=Coalesce(
                Subquery(items_total_amount_subquery),
                Value(0),
                output_field=DecimalField(max_digits=18, decimal_places=4),
            ),
            paid_amount=Coalesce(
                Subquery(paid_amount_subquery),
                Value(0),
                output_field=DecimalField(max_digits=18, decimal_places=4),
            ),
            received_total_amount=Coalesce(
                Subquery(received_total_amount_subquery),
                Value(0),
                output_field=DecimalField(max_digits=18, decimal_places=4),
            ),
            expected_delivery_date_min=Subquery(
                expected_delivery_date_min_subquery,
                output_field=DateField(),
            ),
        ).annotate(
            order_total_amount=ExpressionWrapper(
                F("items_total_amount") - F("discount_amount"),
                output_field=DecimalField(max_digits=18, decimal_places=4),
            ),
        ).annotate(
            payment_completion_threshold=ExpressionWrapper(
                F("order_total_amount") - Value(PAYMENT_COMPLETION_TOLERANCE),
                output_field=DecimalField(max_digits=18, decimal_places=4),
            ),
        ).annotate(
            payment_percent=Case(
                When(order_total_amount__lte=0, then=Value(0)),
                When(paid_amount__gte=F("payment_completion_threshold"), then=Value(100)),
                default=Cast(
                    Least(
                        Value(99),
                        Round(
                            ExpressionWrapper(
                                F("paid_amount") * Value(100.0) / F("order_total_amount"),
                                output_field=DecimalField(max_digits=18, decimal_places=6),
                            )
                        ),
                    ),
                    IntegerField(),
                ),
                output_field=IntegerField(),
            ),
            receipt_percent=Case(
                When(order_total_amount__lte=0, then=Value(0)),
                When(received_total_amount__gte=F("order_total_amount"), then=Value(100)),
                default=Cast(
                    Least(
                        Value(99),
                        Round(
                            ExpressionWrapper(
                                F("received_total_amount") * Value(100.0) / F("order_total_amount"),
                                output_field=DecimalField(max_digits=18, decimal_places=6),
                            )
                        ),
                    ),
                    IntegerField(),
                ),
                output_field=IntegerField(),
            ),
        ).annotate(
            is_receipt_overdue=Case(
                When(
                    receipt_percent__lt=100,
                    expected_delivery_date_min__isnull=False,
                    expected_delivery_date_min__lt=today,
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )

        return queryset

    def get_queryset(self):
        queryset = self._with_registry_annotations(self.queryset)

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(vendor_id__in=vendor)

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        created_by = self.request.query_params.getlist("created_by")
        if created_by:
            queryset = queryset.filter(created_by_id__in=created_by)

        payment_ranges = self.request.query_params.getlist("payment_range")
        if payment_ranges:
            payment_q = Q()
            valid_payment_filter = False

            for value in payment_ranges:
                if value == "0":
                    payment_q |= Q(payment_percent=0)
                    valid_payment_filter = True
                elif value == "1-49":
                    payment_q |= Q(payment_percent__gte=1, payment_percent__lte=49)
                    valid_payment_filter = True
                elif value == "50-99":
                    payment_q |= Q(payment_percent__gte=50, payment_percent__lte=99)
                    valid_payment_filter = True
                elif value == "100":
                    payment_q |= Q(payment_percent=100)
                    valid_payment_filter = True

            if valid_payment_filter:
                queryset = queryset.filter(payment_q)

        receipt_ranges = self.request.query_params.getlist("receipt_range")
        if receipt_ranges:
            receipt_q = Q()
            valid_receipt_filter = False

            for value in receipt_ranges:
                if value == "overdue":
                    receipt_q |= Q(is_receipt_overdue=True)
                    valid_receipt_filter = True
                elif value == "0":
                    receipt_q |= Q(receipt_percent=0)
                    valid_receipt_filter = True
                elif value == "1-49":
                    receipt_q |= Q(receipt_percent__gte=1, receipt_percent__lte=49)
                    valid_receipt_filter = True
                elif value == "50-99":
                    receipt_q |= Q(receipt_percent__gte=50, receipt_percent__lte=99)
                    valid_receipt_filter = True
                elif value == "100":
                    receipt_q |= Q(receipt_percent=100)
                    valid_receipt_filter = True

            if valid_receipt_filter:
                queryset = queryset.filter(receipt_q)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(order_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(vendor__code__icontains=search)
                | models.Q(vendor__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        ordering = self.request.query_params.get("ordering")
        allowed_ordering = {
            "order_total_amount",
            "-order_total_amount",
            "payment_percent",
            "-payment_percent",
            "receipt_percent",
            "-receipt_percent",
        }

        if ordering in allowed_ordering:
            queryset = queryset.order_by(ordering, "-id")

        return queryset

    def perform_create(self, serializer):
        order = serializer.save(created_by=self.request.user)

        create_external_order_event(
            order=order,
            event_type=ExternalOrderEvent.EventType.ORDER_CREATED,
            source=ExternalOrderEvent.Source.PROCUREMENT,
            title="Замовлення створено",
            created_by=self.request.user,
        )

    def _get_affected_inv_item_ids(self, order):
        return list({
            item.vendor_item.item_id
            for item in order.items.select_related(
                "vendor_item",
                "vendor_item__item",
            )
        })

    def _schedule_shortage_recalculation(self, inv_item_ids):
        if not inv_item_ids:
            return

        transaction.on_commit(
            lambda: recalculate_warehouse_shortages_task.delay(
                inv_item_ids=inv_item_ids,
            )
        )

    def _delete_order_and_recalculate(self, order):
        affected_inv_item_ids = self._get_affected_inv_item_ids(order)
        order.delete()
        self._schedule_shortage_recalculation(affected_inv_item_ids)

    def perform_destroy(self, instance):
        if instance.status == ExternalOrder.StatusChoices.DRAFT:
            self._delete_order_and_recalculate(instance)
            return

        if instance.status != ExternalOrder.StatusChoices.IN_PROGRESS:
            raise ValidationError(
                "Цей статус замовлення не дозволяє фізичне видалення."
            )

        if instance.payment_documents.filter(
            status=ExternalPaymentDocument.StatusChoices.PAID,
        ).exists():
            raise ValidationError(
                "Замовлення з оплаченими платежами можна лише скасувати."
            )

        if instance.refund_documents.exists():
            raise ValidationError(
                "Замовлення з поверненнями коштів можна лише скасувати."
            )

        if instance.receipt_documents.exists():
            raise ValidationError(
                "Замовлення з документами приходу можна лише скасувати."
            )

        if instance.reclamation_returns.exists():
            raise ValidationError(
                "Замовлення з рекламаціями можна лише скасувати."
            )

        self._delete_order_and_recalculate(instance)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        order = self.get_object()

        if order.status != ExternalOrder.StatusChoices.IN_PROGRESS:
            raise ValidationError(
                "Скасувати можна лише замовлення у статусі 'В роботі'."
            )

        old_status = order.status
        affected_inv_item_ids = self._get_affected_inv_item_ids(order)

        with transaction.atomic():
            order.status = ExternalOrder.StatusChoices.CANCELLED
            order.save(update_fields=["status"])

            create_external_order_event(
                order=order,
                event_type=ExternalOrderEvent.EventType.ORDER_STATUS_CHANGED,
                source=ExternalOrderEvent.Source.PROCUREMENT,
                title="Замовлення скасовано",
                payload={
                    "from": old_status,
                    "to": order.status,
                },
                created_by=request.user,
            )

            self._schedule_shortage_recalculation(affected_inv_item_ids)

        serializer = self.get_serializer(order)
        return Response(serializer.data)

    def perform_update(self, serializer):
        if serializer.instance.status == ExternalOrder.StatusChoices.COMPLETED:
            raise ValidationError("Замовлення у статусі 'Виконано' не можна змінювати.")

        old_status = serializer.instance.status
        old_comment = serializer.instance.comment or ""

        with transaction.atomic():
            order = serializer.save()
            new_comment = order.comment or ""

            if old_comment != new_comment:
                if not old_comment and new_comment:
                    comment_event_type = ExternalOrderEvent.EventType.COMMENT_ADDED
                    comment_title = "Додано коментар"
                elif old_comment and not new_comment:
                    comment_event_type = ExternalOrderEvent.EventType.COMMENT_DELETED
                    comment_title = "Видалено коментар"
                else:
                    comment_event_type = ExternalOrderEvent.EventType.COMMENT_UPDATED
                    comment_title = "Оновлено коментар"

                create_external_order_event(
                    order=order,
                    event_type=comment_event_type,
                    source=ExternalOrderEvent.Source.PROCUREMENT,
                    title=comment_title,
                    payload={
                        "from": old_comment,
                        "to": new_comment,
                    },
                    created_by=self.request.user,
                )

            if old_status != order.status:
                status_change_title = "Статус замовлення змінено"

                if (
                    old_status == ExternalOrder.StatusChoices.DRAFT
                    and order.status == ExternalOrder.StatusChoices.IN_PROGRESS
                ):
                    status_change_title = "Замовлення підтверджено"

                elif (
                    old_status == ExternalOrder.StatusChoices.IN_PROGRESS
                    and order.status == ExternalOrder.StatusChoices.COMPLETED
                ):
                    status_change_title = "Замовлення завершено"

                elif order.status == ExternalOrder.StatusChoices.CANCELLED:
                    status_change_title = "Замовлення скасовано"

                create_external_order_event(
                    order=order,
                    event_type=ExternalOrderEvent.EventType.ORDER_STATUS_CHANGED,
                    source=ExternalOrderEvent.Source.PROCUREMENT,
                    title=status_change_title,
                    payload={
                        "from": old_status,
                        "to": order.status,
                    },
                    created_by=self.request.user,
                )

            if (
                old_status == ExternalOrder.StatusChoices.DRAFT
                and order.status == ExternalOrder.StatusChoices.IN_PROGRESS
            ):
                items_total_amount = Decimal("0.00")
                for item in order.items.all():
                    items_total_amount += item.quantity * item.agreed_price

                order_total_amount = items_total_amount - order.discount_amount
                auto_payment_no = f"AUTO-{order.order_no}"

                if not ExternalPaymentDocument.objects.filter(payment_no=auto_payment_no).exists():
                    payment_document = ExternalPaymentDocument.objects.create(
                        payment_no=auto_payment_no,
                        order=order,
                        status=ExternalPaymentDocument.StatusChoices.DRAFT,
                        payment_amount=order_total_amount,
                        created_by=self.request.user,
                        comment="Автоматично створено при переведенні замовлення в статус 'В роботі'.",
                    )

                    create_external_order_event(
                        order=order,
                        event_type=ExternalOrderEvent.EventType.PAYMENT_DOCUMENT_CREATED,
                        source=ExternalOrderEvent.Source.SYSTEM,
                        title="Автоматично створено платіжний документ",
                        payload={
                            "payment_document_id": payment_document.id,
                            "payment_no": payment_document.payment_no,
                            "status": payment_document.status,
                            "payment_amount": str(payment_document.payment_amount),
                            "reason": "order_confirmed",
                        },
                        created_by=self.request.user,
                    )

            try_complete_order(order, created_by=self.request.user)

