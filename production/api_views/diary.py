import logging
import os
import traceback

from django.db import transaction

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import DjangoModelPermissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from production.models import (
    ProductionDiaryAttachment,
    ProductionDiaryEntry,
    ProductionOrder,
)
from production.serializers import (
    CreateProductionDiaryEntrySerializer,
    ProductionDiaryEntrySerializer,
    UpdateProductionDiaryEntrySerializer,
)
from sales.models import SalesOrderEvent
from sales.services.events import create_sales_order_event


logger = logging.getLogger(__name__)

class ProductionDiaryEntryViewSet(ModelViewSet):
    http_method_names = [
        "get",
        "post",
        "head",
        "options",
        "delete",
    ]
    permission_classes = [DjangoModelPermissions]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ProductionDiaryEntrySerializer

    queryset = ProductionDiaryEntry.objects.select_related(
        "production_order",
        "production_order__sales_order",
        "production_order_step",
        "author",
    ).prefetch_related(
        "attachments",
    ).order_by(
        "-created_at",
        "-id",
    )

    def get_queryset(self):
        queryset = self.queryset

        production_order = self.request.query_params.get("production_order")
        if production_order:
            queryset = queryset.filter(production_order_id=production_order)

        sales_order = self.request.query_params.get("sales_order")
        if sales_order:
            queryset = queryset.filter(
                production_order__sales_order_id=sales_order,
            )

        production_order_step = self.request.query_params.get(
            "production_order_step"
        )
        if production_order_step:
            queryset = queryset.filter(
                production_order_step_id=production_order_step,
            )

        return queryset

    def _get_attachment_type(self, uploaded_file):
        content_type = uploaded_file.content_type or ""

        if content_type.startswith("image/"):
            return ProductionDiaryAttachment.AttachmentType.PHOTO

        if content_type.startswith("video/"):
            return ProductionDiaryAttachment.AttachmentType.VIDEO

        ext = os.path.splitext(uploaded_file.name)[1].lower()

        if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            return ProductionDiaryAttachment.AttachmentType.PHOTO

        if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            return ProductionDiaryAttachment.AttachmentType.VIDEO

        return ProductionDiaryAttachment.AttachmentType.OTHER

    def create(self, request, *args, **kwargs):
        try:
            serializer = CreateProductionDiaryEntrySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                entry = ProductionDiaryEntry.objects.create(
                    production_order=serializer.validated_data[
                        "production_order"
                    ],
                    production_order_step=serializer.validated_data.get(
                        "production_order_step"
                    ),
                    author=request.user,
                    comment=serializer.validated_data.get("comment", ""),
                )

                for uploaded_file in serializer.validated_data.get(
                    "attachments",
                    [],
                ):
                    ProductionDiaryAttachment.objects.create(
                        entry=entry,
                        file=uploaded_file,
                        attachment_type=self._get_attachment_type(uploaded_file),
                    )

                create_sales_order_event(
                    sales_order=entry.production_order.sales_order,
                    event_type=SalesOrderEvent.EventType.PRODUCTION_DIARY_ENTRY_CREATED,
                    source=SalesOrderEvent.Source.PRODUCTION,
                    title="Додано запис у щоденник",
                    message="Додано новий запис виробничого щоденника.",
                    payload={
                        "diary_entry_id": entry.id,
                        "production_order_id": entry.production_order_id,
                        "production_order_step_id": entry.production_order_step_id,
                        "attachments_count": entry.attachments.count(),
                    },
                    created_by=request.user,
                )

            entry = self.get_queryset().get(pk=entry.pk)

            return Response(
                self.get_serializer(entry).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as exc:
            logger.error("ProductionDiaryEntry create failed: %s", exc)
            logger.error(traceback.format_exc())
            raise

    def update(self, request, *args, **kwargs):
        raise ValidationError("PATCH/PUT не підтримуються для цього endpoint.")

    def partial_update(self, request, *args, **kwargs):
        raise ValidationError("PATCH/PUT не підтримуються для цього endpoint.")

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()

        if entry.production_order.status in [
            ProductionOrder.Status.READY,
            ProductionOrder.Status.CANCELLED,
        ]:
            raise ValidationError(
                "Для цього ProductionOrder редагування щоденника недоступне."
            )

        attachments = list(entry.attachments.all())

        create_sales_order_event(
            sales_order=entry.production_order.sales_order,
            event_type=SalesOrderEvent.EventType.PRODUCTION_DIARY_ENTRY_DELETED,
            source=SalesOrderEvent.Source.PRODUCTION,
            title="Видалено запис щоденника",
            message="Видалено запис виробничого щоденника.",
            payload={
                "diary_entry_id": entry.id,
                "production_order_id": entry.production_order_id,
                "production_order_step_id": entry.production_order_step_id,
                "attachments_count": len(attachments),
            },
            created_by=request.user,
        )

        entry.delete()

        for attachment in attachments:
            attachment.file.delete(save=False)

        return Response(status=204)

    @action(detail=True, methods=["post"], url_path="edit")
    def edit(self, request, *args, **kwargs):
        entry = self.get_object()

        serializer = UpdateProductionDiaryEntrySerializer(
            data=request.data,
            context={
                "entry": entry,
            },
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            comment_updated = False
            production_order_step_updated = False

            if "comment" in serializer.validated_data:
                new_comment = serializer.validated_data["comment"]

                if entry.comment != new_comment:
                    comment_updated = True

                entry.comment = new_comment

            if "production_order_step" in serializer.validated_data:
                new_step = serializer.validated_data[
                    "production_order_step"
                ]

                if entry.production_order_step_id != (
                    new_step.id if new_step else None
                ):
                    production_order_step_updated = True

                entry.production_order_step = new_step

            entry.save()

            delete_attachment_ids = serializer.validated_data.get(
                "delete_attachment_ids",
                [],
            )

            deleted_attachments_count = len(delete_attachment_ids)
            added_attachments_count = len(
                serializer.validated_data.get("attachments", [])
            )

            if delete_attachment_ids:
                attachments_to_delete = list(
                    entry.attachments.filter(
                        id__in=delete_attachment_ids,
                    )
                )

                for attachment in attachments_to_delete:
                    attachment.file.delete(save=False)

                entry.attachments.filter(
                    id__in=delete_attachment_ids,
                ).delete()

            for uploaded_file in serializer.validated_data.get(
                "attachments",
                [],
            ):
                ProductionDiaryAttachment.objects.create(
                    entry=entry,
                    file=uploaded_file,
                    attachment_type=self._get_attachment_type(uploaded_file),
                )

            create_sales_order_event(
                sales_order=entry.production_order.sales_order,
                event_type=SalesOrderEvent.EventType.PRODUCTION_DIARY_ENTRY_UPDATED,
                source=SalesOrderEvent.Source.PRODUCTION,
                title="Оновлено запис щоденника",
                message="Оновлено запис виробничого щоденника.",
                payload={
                    "diary_entry_id": entry.id,
                    "production_order_id": entry.production_order_id,
                    "production_order_step_id": entry.production_order_step_id,
                    "comment_updated": comment_updated,
                    "production_order_step_updated": (
                        production_order_step_updated
                    ),
                    "added_attachments_count": (
                        added_attachments_count
                    ),
                    "deleted_attachments_count": (
                        deleted_attachments_count
                    ),
                },
                created_by=request.user,
            )

        entry = self.get_queryset().get(pk=entry.pk)

        return Response(self.get_serializer(entry).data)