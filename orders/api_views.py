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

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from .models import (
    ExternalOrder,
    ExternalOrderItem,
    ExternalPaymentDocument,
    ExternalReceiptDocument,
    ExternalReceiptItem,
)
from .serializers import (
    ExternalOrderSerializer,
    ExternalOrderItemSerializer,
    ExternalPaymentDocumentSerializer,
    ExternalReceiptDocumentSerializer,
    ExternalReceiptItemSerializer,
)

VAT_RATE = Decimal("0.20")
VAT_DIVISOR = Decimal("1.20")


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


def try_complete_order(order):
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
            received_quantity += receipt_item.received_quantity

        capped_received_quantity = min(received_quantity, item.quantity)
        received_total_amount += capped_received_quantity * item.agreed_price

    payment_percent = 0
    receipt_percent = 0

    if order_total_amount > 0:
        if paid_amount >= order_total_amount:
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
        order.status = ExternalOrder.StatusChoices.COMPLETED
        order.save(update_fields=["status"])

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
                    ExternalReceiptItem.objects.filter(order_item_id=OuterRef("pk"))
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
            payment_percent=Case(
                When(order_total_amount__lte=0, then=Value(0)),
                When(paid_amount__gte=F("order_total_amount"), then=Value(100)),
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
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.status == ExternalOrder.StatusChoices.COMPLETED:
            raise ValidationError("Замовлення у статусі 'Виконано' не можна змінювати.")

        old_status = serializer.instance.status

        with transaction.atomic():
            order = serializer.save()

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
                    ExternalPaymentDocument.objects.create(
                        payment_no=auto_payment_no,
                        order=order,
                        status=ExternalPaymentDocument.StatusChoices.DRAFT,
                        payment_amount=order_total_amount,
                        created_by=self.request.user,
                        comment="Автоматично створено при переведенні замовлення в статус 'В роботі'.",
                    )

            try_complete_order(order)

class ExternalOrderItemViewSet(ModelViewSet):
    queryset = ExternalOrderItem.objects.select_related(
        "order",
        "order__vendor",
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
    ).order_by("order__order_no", "id")
    serializer_class = ExternalOrderItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_id__in=order)

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(order__vendor_id__in=vendor)

        vendor_item = self.request.query_params.getlist("vendor_item")
        if vendor_item:
            queryset = queryset.filter(vendor_item_id__in=vendor_item)

        inv_item = self.request.query_params.getlist("inv_item")
        if inv_item:
            queryset = queryset.filter(vendor_item__item_id__in=inv_item)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(order__order_no__icontains=search)
                | models.Q(vendor_item__vendor_sku__icontains=search)
                | models.Q(vendor_item__name__icontains=search)
                | models.Q(vendor_item__vendor__code__icontains=search)
                | models.Q(vendor_item__vendor__name__icontains=search)
                | models.Q(vendor_item__item__internal_code__icontains=search)
                | models.Q(vendor_item__item__name__icontains=search)
                | models.Q(vendor_item__brand__name__icontains=search)
                | models.Q(vendor_item__country_of_origin__name__icontains=search)
                | models.Q(vendor_item__country_of_origin__code__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            order_item = serializer.save()
            recalculate_order_vat_amount(order_item.order)

    def perform_update(self, serializer):
        with transaction.atomic():
            order_item = serializer.save()
            recalculate_order_vat_amount(order_item.order)

    def perform_destroy(self, instance):
        if instance.order.status != ExternalOrder.StatusChoices.DRAFT:
            raise ValidationError(
                "Видалення рядків замовлення дозволене лише для замовлень у статусі 'Чернетка'."
            )

        order = instance.order

        with transaction.atomic():
            instance.delete()
            recalculate_order_vat_amount(order)

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
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        old_status = serializer.instance.status

        with transaction.atomic():
            payment_document = serializer.save()
            order = payment_document.order

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

            try_complete_order(order)


class ExternalReceiptDocumentViewSet(ModelViewSet):
    queryset = ExternalReceiptDocument.objects.select_related(
        "order",
        "order__vendor",
        "created_by",
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=ExternalReceiptItem.objects.select_related(
                "order_item",
                "order_item__order",
                "order_item__vendor_item",
                "order_item__vendor_item__item",
                "order_item__vendor_item__item__unit",
            ),
        )
    ).order_by("-created_at", "-id")
    serializer_class = ExternalReceiptDocumentSerializer
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
                models.Q(receipt_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(order__order_no__icontains=search)
                | models.Q(order__vendor__code__icontains=search)
                | models.Q(order__vendor__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExternalReceiptItemViewSet(ModelViewSet):
    queryset = ExternalReceiptItem.objects.select_related(
        "receipt_document",
        "receipt_document__order",
        "order_item",
        "order_item__order",
        "order_item__vendor_item",
        "order_item__vendor_item__item",
        "order_item__vendor_item__item__unit",
    ).order_by("receipt_document__receipt_no", "id")
    serializer_class = ExternalReceiptItemSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        queryset = self.queryset

        receipt_document = self.request.query_params.getlist("receipt_document")
        if receipt_document:
            queryset = queryset.filter(receipt_document_id__in=receipt_document)

        order = self.request.query_params.getlist("order")
        if order:
            queryset = queryset.filter(order_item__order_id__in=order)

        vendor = self.request.query_params.getlist("vendor")
        if vendor:
            queryset = queryset.filter(order_item__order__vendor_id__in=vendor)

        order_item = self.request.query_params.getlist("order_item")
        if order_item:
            queryset = queryset.filter(order_item_id__in=order_item)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(receipt_document__receipt_no__icontains=search)
                | models.Q(order_item__order__order_no__icontains=search)
                | models.Q(order_item__vendor_item__vendor_sku__icontains=search)
                | models.Q(order_item__vendor_item__name__icontains=search)
                | models.Q(order_item__vendor_item__item__internal_code__icontains=search)
                | models.Q(order_item__vendor_item__item__name__icontains=search)
            )

        return queryset
        
    def perform_create(self, serializer):
        with transaction.atomic():
            receipt_item = serializer.save()
            try_complete_order(receipt_item.order_item.order)

    def perform_update(self, serializer):
        with transaction.atomic():
            receipt_item = serializer.save()
            try_complete_order(receipt_item.order_item.order)