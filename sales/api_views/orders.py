import logging
import traceback

from django.db import models


logger = logging.getLogger(__name__)

from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from sales.services.orders import check_sales_order_can_confirm

from sales.models import SalesOrder
from sales.serializers import (
    SalesOrderSerializer,
    SalesOrderListSerializer,
    CreateSalesOrderSerializer,
    UpdateSalesOrderComponentSourceSerializer,
)
from sales.services.orders import create_sales_order


class SalesOrderViewSet(ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    queryset = SalesOrder.objects.select_related(
        "organization",
        "product",
        "created_by",
        "customer_responsible_person",
    ).prefetch_related(
        "components",
        "components__inv_item",
    ).order_by("-created_at", "-id")

    serializer_class = SalesOrderSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return SalesOrderListSerializer
        return SalesOrderSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception as exc:
            logger.error("SalesOrder retrieve failed: %s", exc)
            logger.error(traceback.format_exc())
            raise

    def get_queryset(self):
        queryset = self.queryset

        ordering = self.request.query_params.get("ordering")
        if ordering in ["created_at", "-created_at", "completed_at", "-completed_at"]:
            queryset = queryset.order_by(ordering)

        status = self.request.query_params.getlist("status")
        if status:
            queryset = queryset.filter(status__in=status)

        created_at_from = self.request.query_params.get("created_at_from")
        if created_at_from:
            queryset = queryset.filter(created_at__gte=created_at_from)

        created_at_to = self.request.query_params.get("created_at_to")
        if created_at_to:
            queryset = queryset.filter(created_at__lte=created_at_to)

        completed_at_from = self.request.query_params.get("completed_at_from")
        if completed_at_from:
            queryset = queryset.filter(completed_at__gte=completed_at_from)

        completed_at_to = self.request.query_params.get("completed_at_to")
        if completed_at_to:
            queryset = queryset.filter(completed_at__lte=completed_at_to)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(organization__name__icontains=search)
                | models.Q(product__code__icontains=search)
                | models.Q(product__product_family__name__icontains=search)
            )

        return queryset
    permission_classes = [DjangoModelPermissions]

    def create(self, request, *args, **kwargs):
        serializer = CreateSalesOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sales_order = create_sales_order(
            organization=serializer.validated_data["organization"],
            product=serializer.validated_data["product"],
            created_by=request.user if request.user.is_authenticated else None,
            customer_responsible_person=serializer.validated_data.get("customer_responsible_person"),
            comment=serializer.validated_data.get("comment", ""),
        )

        sales_order = self.get_queryset().get(pk=sales_order.pk)

        return Response(SalesOrderListSerializer(sales_order).data)
        
    @action(detail=True, methods=["post"], url_path="update-component-source")
    def update_component_source(self, request, pk=None):
        sales_order = self.get_object()

        if sales_order.status != SalesOrder.Status.DRAFT:
            raise ValidationError(
                "Джерело компонента можна змінювати лише для замовлення в статусі draft."
            )

        serializer = UpdateSalesOrderComponentSourceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        component_id = serializer.validated_data["component_id"]

        try:
            component = sales_order.components.get(id=component_id)
        except sales_order.components.model.DoesNotExist:
            raise ValidationError("Компонент замовлення не знайдено.")

        component.source_type = serializer.validated_data["source_type"]

        if component.source_type == component.SourceType.DONATED:
            component.source_organization = serializer.validated_data.get("source_organization")
        else:
            component.source_organization = None

        component.save(update_fields=["source_type", "source_organization"])

        sales_order = self.get_queryset().get(pk=sales_order.pk)

        return Response(self.get_serializer(sales_order).data)
        
    @action(detail=True, methods=["get"], url_path="confirmation-status")
    def confirmation_status(self, request, pk=None):
        sales_order = self.get_object()

        result = check_sales_order_can_confirm(sales_order)

        return Response(result)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        sales_order = self.get_object()

        result = check_sales_order_can_confirm(sales_order)

        if not result["can_confirm"]:
            return Response(result, status=400)

        sales_order.status = SalesOrder.Status.CONFIRMED
        sales_order.save(update_fields=["status"])

        sales_order = self.get_queryset().get(pk=sales_order.pk)

        return Response(self.get_serializer(sales_order).data)