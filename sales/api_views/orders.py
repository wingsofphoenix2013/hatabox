import logging
import traceback

from django.db import models, transaction
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404


logger = logging.getLogger(__name__)

from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from sales.services.orders import (
    create_sales_order,
    check_sales_order_can_confirm,
)
from production.models import ProductionOrder, ProductionOrderStep
from production.services.orders import (
    create_production_order_from_sales_order,
)
from warehouse.services.production_reservation import (
    reserve_customer_components_for_confirmation,
    cancel_sales_order_warehouse_state,
)
from warehouse.tasks import recalculate_warehouse_shortages_task
from sales.services.issues import (
    recalculate_customer_component_confirmation_issues,
)

from sales.models import SalesOrder, SalesOrderComponent, SalesOrderIssue
from sales.serializers import (
    SalesOrderComponentSerializer,
    SalesOrderSerializer,
    SalesOrderListSerializer,
    CreateSalesOrderSerializer,
    UpdateSalesOrderComponentSourceSerializer,
    SetCustomerComponentsSerializer,
    UpdateSalesOrderDetailsSerializer,
    SalesOrderProductionReadinessSerializer,
    SalesOrderEventSerializer,
    ChangeSalesOrderProductSerializer,
)
from sales.models import (
    SalesOrder,
    SalesOrderComponent,
    SalesOrderIssue,
    SalesOrderEvent,
)
from sales.services.orders import (
    create_sales_order,
    check_sales_order_can_confirm,
)
from sales.services.change_product import (
    change_sales_order_product,
)
from sales.services.orders import create_sales_order
from sales.services.production_readiness import (
    build_sales_order_production_readiness,
)
from sales.services.events import (
    create_sales_order_event,
    build_sales_order_events,
)


class SalesOrderViewSet(ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    queryset = SalesOrder.objects.select_related(
        "organization",
        "product",
        "created_by",
        "customer_responsible_person",
        "production_order",
    ).annotate(
        open_confirmation_issues_count=models.Count(
            "issues",
            filter=models.Q(
                issues__stage=SalesOrderIssue.Stage.CONFIRMATION,
                issues__status=SalesOrderIssue.Status.OPEN,
            ),
        ),
        open_critical_confirmation_issues_count=models.Count(
            "issues",
            filter=models.Q(
                issues__stage=SalesOrderIssue.Stage.CONFIRMATION,
                issues__status=SalesOrderIssue.Status.OPEN,
                issues__severity=SalesOrderIssue.Severity.CRITICAL,
            ),
        ),
        production_order_first_step_confirmed=Exists(
            ProductionOrderStep.objects.filter(
                production_order__sales_order=OuterRef("pk"),
                sequence_number=1,
                status=ProductionOrderStep.Status.CONFIRMED,
            )
        ),
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
                | models.Q(production_order__serial_number__icontains=search)
            )

        return queryset
    permission_classes = [DjangoModelPermissions]

    def create(self, request, *args, **kwargs):
        try:
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

        except Exception as exc:
            logger.error("SalesOrder create failed: %s", exc)
            logger.error(traceback.format_exc())
            raise
        
    @action(detail=True, methods=["post"], url_path="update-component-fulfillment")
    def update_component_fulfillment(self, request, pk=None):
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

        component.fulfillment_mode = serializer.validated_data["fulfillment_mode"]

        component.save(update_fields=["fulfillment_mode"])

        sales_order = self.get_queryset().get(pk=sales_order.pk)

        return Response(self.get_serializer(sales_order).data)
        
    @action(detail=True, methods=["post"], url_path="update-details")
    def update_details(self, request, pk=None):
        sales_order = self.get_object()

        if sales_order.status in [
            SalesOrder.Status.COMPLETED,
            SalesOrder.Status.CANCELLED,
        ]:
            raise ValidationError(
                "Неможливо змінювати деталі завершеного або скасованого замовлення."
            )

        serializer = UpdateSalesOrderDetailsSerializer(
            data=request.data,
            context={
                "sales_order": sales_order,
            },
        )
        serializer.is_valid(raise_exception=True)

        changed_fields = {}

        if "comment" in serializer.validated_data:
            old_comment = sales_order.comment
            new_comment = serializer.validated_data["comment"]

            if old_comment != new_comment:
                changed_fields["comment"] = {
                    "old": old_comment,
                    "new": new_comment,
                }

            sales_order.comment = new_comment

        if "customer_responsible_person" in serializer.validated_data:
            old_person_id = sales_order.customer_responsible_person_id
            new_person = serializer.validated_data[
                "customer_responsible_person"
            ]

            if old_person_id != (
                new_person.id if new_person else None
            ):
                changed_fields["customer_responsible_person"] = {
                    "old": old_person_id,
                    "new": (
                        new_person.id
                        if new_person
                        else None
                    ),
                }

            sales_order.customer_responsible_person = new_person

        sales_order.save(
            update_fields=[
                "comment",
                "customer_responsible_person",
                "updated_at",
            ]
        )

        if changed_fields:
            create_sales_order_event(
                sales_order=sales_order,
                event_type=SalesOrderEvent.EventType.SALES_ORDER_DETAILS_UPDATED,
                source=SalesOrderEvent.Source.SALES,
                title="Оновлено деталі SalesOrder",
                message="Оновлено деталі замовлення.",
                payload={
                    "changed_fields": changed_fields,
                },
                created_by=request.user,
            )

        sales_order = self.get_queryset().get(pk=sales_order.pk)

        return Response(self.get_serializer(sales_order).data)

    @action(detail=True, methods=["get"], url_path="components")
    def components(self, request, pk=None):
        sales_order = self.get_object()

        components = sales_order.components.select_related(
            "inv_item",
        ).order_by(
            "inv_item__name",
            "id",
        )

        serializer = SalesOrderComponentSerializer(
            components,
            many=True,
        )

        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="set-customer-components")
    def set_customer_components(self, request, pk=None):
        sales_order = self.get_object()

        if sales_order.status != SalesOrder.Status.DRAFT:
            raise ValidationError(
                "Компоненти замовника можна змінювати лише для замовлення в статусі draft."
            )

        serializer = SetCustomerComponentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        component_ids = set(serializer.validated_data["component_ids"])

        order_component_ids = set(
            sales_order.components.values_list("id", flat=True)
        )

        invalid_ids = component_ids - order_component_ids

        if invalid_ids:
            raise ValidationError({
                "component_ids": "Передано компоненти, які не належать до цього замовлення."
            })

        sales_order.components.update(
            fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
        )

        sales_order.components.filter(
            id__in=component_ids,
        ).update(
            fulfillment_mode=SalesOrderComponent.FulfillmentMode.CUSTOMER,
        )

        affected_inv_item_ids = set(
            sales_order.components.filter(
                id__in=component_ids,
            ).values_list("inv_item_id", flat=True)
        )

        for inv_item_id in affected_inv_item_ids:
            recalculate_customer_component_confirmation_issues(
                organization_id=sales_order.organization_id,
                inv_item_id=inv_item_id,
            )

        sales_order = self.get_queryset().get(pk=sales_order.pk)

        return Response(self.get_serializer(sales_order).data)

    @action(detail=True, methods=["post"], url_path="change-product")
    def change_product(self, request, pk=None):
        sales_order = self.get_object()

        serializer = ChangeSalesOrderProductSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        result = change_sales_order_product(
            sales_order=sales_order,
            new_product=serializer.validated_data["product"],
            created_by=request.user,
        )

        sales_order = self.get_queryset().get(
            pk=sales_order.pk,
        )

        return Response({
            "sales_order": self.get_serializer(
                sales_order,
            ).data,
            "result": result,
        })

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        try:
            with transaction.atomic():
                sales_order = get_object_or_404(
                    SalesOrder.objects.select_for_update(),
                    pk=pk,
                )
                self.check_object_permissions(request, sales_order)

                logger.info(
                    "SalesOrder cancel request: id=%s status=%s user=%s",
                    sales_order.id,
                    sales_order.status,
                    request.user,
                )

                affected_inv_item_ids = set(
                    sales_order.components.filter(
                        fulfillment_mode=SalesOrderComponent.FulfillmentMode.CUSTOMER,
                    ).values_list("inv_item_id", flat=True)
                )

                mixed_inv_item_ids = []

                if sales_order.status == SalesOrder.Status.CONFIRMED:
                    mixed_inv_item_ids = list(
                        sales_order.components.filter(
                            fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
                        ).values_list(
                            "inv_item_id",
                            flat=True,
                        ).distinct()
                    )

                    cancel_sales_order_warehouse_state(
                        sales_order=sales_order,
                    )

                elif sales_order.status != SalesOrder.Status.DRAFT:
                    raise ValidationError(
                        "Скасувати можна лише SalesOrder у статусі draft або confirmed."
                    )

                sales_order.status = SalesOrder.Status.CANCELLED
                sales_order.save(update_fields=["status", "updated_at"])

                production_order = ProductionOrder.objects.filter(
                    sales_order=sales_order,
                ).first()

                cancelled_steps_count = 0

                if production_order is not None:
                    production_order.status = ProductionOrder.Status.CANCELLED
                    production_order.save(update_fields=["status"])

                    cancelled_steps_count = ProductionOrderStep.objects.filter(
                        production_order=production_order,
                    ).update(
                        status=ProductionOrderStep.Status.CANCELLED,
                    )

                for inv_item_id in affected_inv_item_ids:
                    recalculate_customer_component_confirmation_issues(
                        organization_id=sales_order.organization_id,
                        inv_item_id=inv_item_id,
                    )

                create_sales_order_event(
                    sales_order=sales_order,
                    event_type=SalesOrderEvent.EventType.SALES_ORDER_CANCELLED,
                    source=SalesOrderEvent.Source.SALES,
                    title="SalesOrder скасовано",
                    message="Замовлення скасовано.",
                    payload={
                        "from_status": (
                            SalesOrder.Status.CONFIRMED
                            if mixed_inv_item_ids
                            else SalesOrder.Status.DRAFT
                        ),
                        "to_status": SalesOrder.Status.CANCELLED,
                    },
                    created_by=request.user,
                )

                if production_order is not None:
                    create_sales_order_event(
                        sales_order=sales_order,
                        event_type=SalesOrderEvent.EventType.PRODUCTION_ORDER_CANCELLED,
                        source=SalesOrderEvent.Source.PRODUCTION,
                        title="ProductionOrder скасовано",
                        message="Карту виробничого процесу скасовано.",
                        payload={
                            "production_order_id": production_order.id,
                            "cancelled_steps_count": cancelled_steps_count,
                        },
                        created_by=request.user,
                    )

                if mixed_inv_item_ids:
                    transaction.on_commit(
                        lambda: recalculate_warehouse_shortages_task.delay(
                            inv_item_ids=mixed_inv_item_ids,
                        )
                    )

            sales_order = self.get_queryset().get(pk=sales_order.pk)

            return Response(self.get_serializer(sales_order).data)

        except Exception as exc:
            logger.error("SalesOrder cancel failed: %s", exc)
            logger.error(traceback.format_exc())
            raise

    @action(detail=True, methods=["get"], url_path="confirmation-status")
    def confirmation_status(self, request, pk=None):
        sales_order = self.get_object()

        open_issues = sales_order.issues.filter(
            stage=SalesOrderIssue.Stage.CONFIRMATION,
            status=SalesOrderIssue.Status.OPEN,
            severity=SalesOrderIssue.Severity.CRITICAL,
        ).select_related(
            "related_inv_item",
            "related_component",
        )

        missing_components = [
            {
                "component_id": issue.related_component_id,
                "inv_item": issue.related_inv_item_id,
                "inv_item_code": (
                    issue.related_inv_item.internal_code
                    if issue.related_inv_item
                    else None
                ),
                "inv_item_name": (
                    issue.related_inv_item.name
                    if issue.related_inv_item
                    else None
                ),
                "required_quantity": (
                    issue.related_component.quantity
                    if issue.related_component
                    else None
                ),
                "available_quantity": (
                    issue.related_component.quantity - issue.missing_quantity
                    if issue.related_component and issue.missing_quantity is not None
                    else None
                ),
                "missing_quantity": issue.missing_quantity,
            }
            for issue in open_issues
        ]

        return Response({
            "can_confirm": len(missing_components) == 0,
            "missing_components": missing_components,
        })
        
    @action(detail=True, methods=["get"], url_path="production-readiness")
    def production_readiness(self, request, pk=None):
        sales_order = self.get_object()

        data = build_sales_order_production_readiness(
            sales_order=sales_order,
        )

        serializer = SalesOrderProductionReadinessSerializer(data)

        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="events")
    def events(self, request, pk=None):
        try:
            sales_order = self.get_object()

            rows = build_sales_order_events(
                sales_order=sales_order,
            )

            page = self.paginate_queryset(rows)

            if page is not None:
                serializer = SalesOrderEventSerializer(
                    page,
                    many=True,
                )
                return self.get_paginated_response(serializer.data)

            serializer = SalesOrderEventSerializer(
                rows,
                many=True,
            )

            return Response(serializer.data)

        except Exception as exc:
            import sys
            import traceback

            print(
                f"SalesOrder events failed: sales_order_id={pk} error={exc}",
                file=sys.stderr,
                flush=True,
            )
            print(
                traceback.format_exc(),
                file=sys.stderr,
                flush=True,
            )

            raise

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        try:
            logger.info(
                "SalesOrder confirm started: id=%s user=%s",
                pk,
                request.user,
            )

            with transaction.atomic():
                sales_order = get_object_or_404(
                    SalesOrder.objects.select_for_update(),
                    pk=pk,
                )
                self.check_object_permissions(request, sales_order)

                logger.info(
                    "SalesOrder confirm locked: id=%s status=%s organization_id=%s",
                    sales_order.id,
                    sales_order.status,
                    sales_order.organization_id,
                )

                if sales_order.status != SalesOrder.Status.DRAFT:
                    raise ValidationError(
                        "Підтвердити можна лише SalesOrder у статусі draft."
                    )

                result = check_sales_order_can_confirm(sales_order)

                logger.info(
                    "SalesOrder confirm check result: id=%s can_confirm=%s missing_components=%s",
                    sales_order.id,
                    result["can_confirm"],
                    len(result.get("missing_components", [])),
                )

                if not result["can_confirm"]:
                    return Response(result, status=400)

                affected_inv_item_ids = set(
                    sales_order.components.filter(
                        fulfillment_mode=SalesOrderComponent.FulfillmentMode.CUSTOMER,
                    ).values_list("inv_item_id", flat=True)
                )

                logger.info(
                    "SalesOrder confirm affected customer items: id=%s inv_item_ids=%s",
                    sales_order.id,
                    sorted(affected_inv_item_ids),
                )

                reserve_customer_components_for_confirmation(
                    sales_order=sales_order,
                    created_by=request.user if request.user.is_authenticated else None,
                )

                logger.info(
                    "SalesOrder confirm reservation completed: id=%s",
                    sales_order.id,
                )

                sales_order.status = SalesOrder.Status.CONFIRMED
                sales_order.save(update_fields=["status", "updated_at"])

                logger.info(
                    "SalesOrder confirm status updated: id=%s status=%s",
                    sales_order.id,
                    sales_order.status,
                )

                production_order = create_production_order_from_sales_order(
                    sales_order=sales_order,
                )

                create_sales_order_event(
                    sales_order=sales_order,
                    event_type=SalesOrderEvent.EventType.SALES_ORDER_CONFIRMED,
                    source=SalesOrderEvent.Source.SALES,
                    title="SalesOrder підтверджено",
                    message="Замовлення підтверджено та підготовлено до виробництва.",
                    payload={
                        "from_status": SalesOrder.Status.DRAFT,
                        "to_status": SalesOrder.Status.CONFIRMED,
                    },
                    created_by=request.user,
                )

                create_sales_order_event(
                    sales_order=sales_order,
                    event_type=SalesOrderEvent.EventType.PRODUCTION_ORDER_CREATED,
                    source=SalesOrderEvent.Source.PRODUCTION,
                    title="Створено ProductionOrder",
                    message="Для замовлення автоматично створено карту виробничого процесу.",
                    payload={
                        "production_order_id": production_order.id,
                    },
                    created_by=request.user,
                )

                logger.info(
                    "ProductionOrder created: id=%s sales_order_id=%s",
                    production_order.id,
                    sales_order.id,
                )

                for inv_item_id in affected_inv_item_ids:
                    logger.info(
                        "SalesOrder confirm recalculation started: id=%s inv_item_id=%s",
                        sales_order.id,
                        inv_item_id,
                    )
                    recalculate_customer_component_confirmation_issues(
                        organization_id=sales_order.organization_id,
                        inv_item_id=inv_item_id,
                    )
                    logger.info(
                        "SalesOrder confirm recalculation finished: id=%s inv_item_id=%s",
                        sales_order.id,
                        inv_item_id,
                    )

                mixed_inv_item_ids = list(
                    sales_order.components.filter(
                        fulfillment_mode=SalesOrderComponent.FulfillmentMode.MIXED,
                    ).values_list(
                        "inv_item_id",
                        flat=True,
                    ).distinct()
                )

                transaction.on_commit(
                    lambda: recalculate_warehouse_shortages_task.delay(
                        inv_item_ids=mixed_inv_item_ids,
                    )
                )

            sales_order = self.get_queryset().get(pk=sales_order.pk)

            logger.info(
                "SalesOrder confirm finished: id=%s",
                sales_order.id,
            )

            return Response(self.get_serializer(sales_order).data)

        except Exception as exc:
            import sys
            import traceback

            print(
                f"SalesOrder confirm failed: sales_order_id={pk} error={exc}",
                file=sys.stderr,
                flush=True,
            )
            print(
                traceback.format_exc(),
                file=sys.stderr,
                flush=True,
            )

            raise