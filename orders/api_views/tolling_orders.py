from datetime import date
from decimal import Decimal

from django.db import IntegrityError, models, transaction
from django.db.models import Prefetch

from rest_framework.permissions import DjangoModelPermissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from orders.models import (
    TollingOrder,
    TollingOrderItem,
    TollingReceiptDocument,
    TollingReceiptItem,
)

from orders.serializers import (
    TollingOrderRegisterLightSerializer,
    TollingOrderSerializer,
)

def try_complete_tolling_order(order):
    if order.status == TollingOrder.StatusChoices.DRAFT:
        return

    has_items = False

    for item in order.items.all():
        has_items = True
        received_quantity = Decimal("0.000")

        for receipt_item in item.receipt_items.all():
            if receipt_item.receipt_document.completed:
                received_quantity += receipt_item.received_quantity

        if received_quantity < item.quantity:
            return

    if (
        has_items
        and order.status != TollingOrder.StatusChoices.COMPLETED
    ):
        order.status = TollingOrder.StatusChoices.COMPLETED
        order.save(update_fields=["status"])
        
def generate_tolling_order_no():
    today = date.today()
    prefix = today.strftime("%d%m%Y")

    existing_numbers = TollingOrder.objects.filter(
        created_at__date=today,
        order_no__startswith=f"{prefix}_",
    ).values_list("order_no", flat=True)

    max_index = 0
    for number in existing_numbers:
        suffix = number.removeprefix(f"{prefix}_")
        if suffix.isdigit():
            max_index = max(max_index, int(suffix))

    return f"{prefix}_{max_index + 1}"
    
def generate_tolling_receipt_no(order):
    base = order.order_no

    existing_numbers = TollingReceiptDocument.objects.filter(
        order=order,
        receipt_no__startswith=f"{base}_r_",
    ).values_list("receipt_no", flat=True)

    max_index = 0
    for number in existing_numbers:
        suffix = number.removeprefix(f"{base}_r_")
        if suffix.isdigit():
            max_index = max(max_index, int(suffix))

    return f"{base}_r_{max_index + 1}"
    
def create_tolling_receipt_draft_from_order(order, created_by):
    receipt_document = TollingReceiptDocument.objects.create(
        receipt_no=generate_tolling_receipt_no(order),
        order=order,
        receipt_date=date.today(),
        completed=False,
        sent_to_warehouse=False,
        created_by=created_by,
        comment="Автоматично створено при переведенні замовлення в статус 'Активне'.",
    )

    receipt_items = [
        TollingReceiptItem(
            receipt_document=receipt_document,
            order_item=order_item,
            received_quantity=order_item.quantity,
        )
        for order_item in order.items.all()
    ]

    if receipt_items:
        TollingReceiptItem.objects.bulk_create(receipt_items)

    return receipt_document

def validate_tolling_receipt_before_completion(receipt_document):
    receipt_items = list(receipt_document.items.select_related("order_item"))

    if not receipt_items:
        raise ValidationError(
            "Неможливо завершити документ приходу без рядків."
        )

    for receipt_item in receipt_items:
        if receipt_item.received_quantity <= 0:
            raise ValidationError(
                "У завершеному документі приходу всі рядки повинні мати кількість більше 0."
            )


def create_next_tolling_receipt_draft_from_remainders(order, created_by):
    remainder_items = []

    order_items = list(order.items.all())

    for order_item in order_items:
        completed_received_quantity = Decimal("0.000")

        for receipt_item in order_item.receipt_items.select_related("receipt_document"):
            if receipt_item.receipt_document.completed:
                completed_received_quantity += receipt_item.received_quantity

        remaining_quantity = order_item.quantity - completed_received_quantity
        if remaining_quantity > 0:
            remainder_items.append((order_item, remaining_quantity))

    if not remainder_items:
        return None

    receipt_document = TollingReceiptDocument.objects.create(
        receipt_no=generate_tolling_receipt_no(order),
        order=order,
        receipt_date=date.today(),
        completed=False,
        sent_to_warehouse=False,
        created_by=created_by,
        comment="Автоматично створено на залишок після завершення попереднього документа приходу.",
    )

    TollingReceiptItem.objects.bulk_create([
        TollingReceiptItem(
            receipt_document=receipt_document,
            order_item=order_item,
            received_quantity=remaining_quantity,
        )
        for order_item, remaining_quantity in remainder_items
    ])

    return receipt_document

class TollingOrderRegisterLightViewSet(ModelViewSet):
    queryset = TollingOrder.objects.select_related(
        "organization",
        "created_by",
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=TollingOrderItem.objects.select_related(
                "inv_item",
                "inv_item__category",
                "inv_item__unit",
            ).prefetch_related(
                Prefetch(
                    "receipt_items",
                    queryset=TollingReceiptItem.objects.select_related("receipt_document"),
                    to_attr="prefetched_receipt_items",
                )
            ),
            to_attr="prefetched_items",
        )
    ).order_by("-created_at", "-id")
    serializer_class = TollingOrderRegisterLightSerializer
    permission_classes = [DjangoModelPermissions]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = self.queryset

        organization = self.request.query_params.getlist("organization")
        if organization:
            queryset = queryset.filter(organization_id__in=organization)

        organization_type = self.request.query_params.get("organization_type")
        if organization_type in ["military", "commercial", "charity"]:
            queryset = queryset.filter(organization__type=organization_type)

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        created_at_from = self.request.query_params.get("created_at_from")
        if created_at_from:
            queryset = queryset.filter(created_at__date__gte=created_at_from)

        created_at_to = self.request.query_params.get("created_at_to")
        if created_at_to:
            queryset = queryset.filter(created_at__date__lte=created_at_to)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(order_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(organization__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset


class TollingOrderViewSet(ModelViewSet):
    queryset = TollingOrder.objects.select_related(
        "organization",
        "created_by",
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=TollingOrderItem.objects.select_related(
                "inv_item",
                "inv_item__category",
                "inv_item__unit",
            ).prefetch_related(
                Prefetch(
                    "receipt_items",
                    queryset=TollingReceiptItem.objects.select_related("receipt_document"),
                    to_attr="prefetched_receipt_items",
                )
            ),
            to_attr="prefetched_items",
        )
    ).order_by("-created_at", "-id")
    serializer_class = TollingOrderSerializer
    permission_classes = [DjangoModelPermissions]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = self.queryset

        organization = self.request.query_params.getlist("organization")
        if organization:
            queryset = queryset.filter(organization_id__in=organization)

        organization_type = self.request.query_params.get("organization_type")
        if organization_type in ["military", "commercial", "charity"]:
            queryset = queryset.filter(organization__type=organization_type)

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        created_at_from = self.request.query_params.get("created_at_from")
        if created_at_from:
            queryset = queryset.filter(created_at__date__gte=created_at_from)

        created_at_to = self.request.query_params.get("created_at_to")
        if created_at_to:
            queryset = queryset.filter(created_at__date__lte=created_at_to)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(order_no__icontains=search)
                | models.Q(comment__icontains=search)
                | models.Q(organization__name__icontains=search)
                | models.Q(created_by__username__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        for _ in range(5):
            try:
                with transaction.atomic():
                    order_no = generate_tolling_order_no()

                    return serializer.save(
                        order_no=order_no,
                        created_by=self.request.user,
                    )
            except IntegrityError:
                continue

        raise ValidationError(
            "Не вдалося згенерувати унікальний номер замовлення. Спробуйте ще раз."
        )

    def perform_update(self, serializer):
        if serializer.instance.status == TollingOrder.StatusChoices.COMPLETED:
            raise ValidationError("Замовлення у статусі 'Виконано' не можна змінювати.")

        old_status = serializer.instance.status

        with transaction.atomic():
            order = serializer.save()

            if (
                old_status == TollingOrder.StatusChoices.DRAFT
                and order.status == TollingOrder.StatusChoices.ACTIVE
            ):
                if not order.items.exists():
                    raise ValidationError(
                        "Неможливо перевести замовлення в статус 'Активне' без рядків."
                    )

                existing_draft_receipt = TollingReceiptDocument.objects.filter(
                    order=order,
                    completed=False,
                ).exists()

                if existing_draft_receipt:
                    raise ValidationError(
                        "Для цього замовлення вже існує незавершений документ приходу."
                    )

                create_tolling_receipt_draft_from_order(
                    order=order,
                    created_by=self.request.user,
                )

            try_complete_tolling_order(order)
