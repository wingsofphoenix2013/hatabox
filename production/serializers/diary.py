from rest_framework import serializers

from production.models import (
    ProductionDiaryAttachment,
    ProductionDiaryEntry,
    ProductionOrder,
    ProductionOrderStep,
)


class ProductionDiaryAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.FileField(
        source="file",
        read_only=True,
    )

    filename = serializers.SerializerMethodField()

    class Meta:
        model = ProductionDiaryAttachment
        fields = [
            "id",
            "attachment_type",
            "file_url",
            "filename",
            "created_at",
        ]

    def get_filename(self, obj):
        return obj.file.name.split("/")[-1]


class ProductionDiaryEntrySerializer(serializers.ModelSerializer):
    attachments = ProductionDiaryAttachmentSerializer(
        many=True,
        read_only=True,
    )

    sales_order = serializers.IntegerField(
        source="production_order.sales_order_id",
        read_only=True,
    )

    author_username = serializers.CharField(
        source="author.username",
        read_only=True,
    )

    production_order_status = serializers.CharField(
        source="production_order.status",
        read_only=True,
    )

    production_order_step_name = serializers.CharField(
        source="production_order_step.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ProductionDiaryEntry
        fields = [
            "id",
            "production_order",
            "sales_order",
            "production_order_status",
            "production_order_step",
            "production_order_step_name",
            "author",
            "author_username",
            "comment",
            "created_at",
            "attachments",
        ]


class CreateProductionDiaryEntrySerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if "attachments[]" in data and "attachments" not in data:
            mutable = getattr(data, "_mutable", None)
            if mutable is not None:
                data._mutable = True

            data.setlist("attachments", data.getlist("attachments[]"))

            if mutable is not None:
                data._mutable = mutable

        return super().to_internal_value(data)

    production_order = serializers.PrimaryKeyRelatedField(
        queryset=ProductionOrder.objects.all(),
    )

    production_order_step = serializers.PrimaryKeyRelatedField(
        queryset=ProductionOrderStep.objects.all(),
        required=False,
        allow_null=True,
    )

    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        production_order = attrs["production_order"]
        production_order_step = attrs.get("production_order_step")

        if production_order.status in [
            ProductionOrder.Status.READY,
            ProductionOrder.Status.CANCELLED,
        ]:
            raise serializers.ValidationError(
                "Для цього ProductionOrder редагування щоденника недоступне."
            )

        if (
            production_order_step is not None
            and production_order_step.production_order_id != production_order.id
        ):
            raise serializers.ValidationError({
                "production_order_step": (
                    "Етап не належить до цього ProductionOrder."
                )
            })

        comment = attrs.get("comment", "").strip()
        attachments = attrs.get("attachments", [])

        if not comment and not attachments:
            raise serializers.ValidationError(
                "Запис щоденника не може бути порожнім."
            )

        return attrs


class UpdateProductionDiaryEntrySerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if "attachments[]" in data and "attachments" not in data:
            mutable = getattr(data, "_mutable", None)
            if mutable is not None:
                data._mutable = True

            data.setlist("attachments", data.getlist("attachments[]"))

            if mutable is not None:
                data._mutable = mutable

        return super().to_internal_value(data)

    production_order_step = serializers.PrimaryKeyRelatedField(
        queryset=ProductionOrderStep.objects.all(),
        required=False,
        allow_null=True,
    )

    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True,
    )

    delete_attachment_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        entry = self.context["entry"]

        if entry.production_order.status in [
            ProductionOrder.Status.READY,
            ProductionOrder.Status.CANCELLED,
        ]:
            raise serializers.ValidationError(
                "Для цього ProductionOrder редагування щоденника недоступне."
            )

        production_order_step = attrs.get("production_order_step")

        if (
            production_order_step is not None
            and production_order_step.production_order_id
            != entry.production_order_id
        ):
            raise serializers.ValidationError({
                "production_order_step": (
                    "Етап не належить до цього ProductionOrder."
                )
            })

        delete_attachment_ids = attrs.get(
            "delete_attachment_ids",
            [],
        )

        existing_attachment_ids = set(
            entry.attachments.values_list("id", flat=True)
        )

        invalid_attachment_ids = (
            set(delete_attachment_ids)
            - existing_attachment_ids
        )

        if invalid_attachment_ids:
            raise serializers.ValidationError({
                "delete_attachment_ids": (
                    "Передано attachment, який не належить запису."
                )
            })

        comment = attrs.get("comment", entry.comment).strip()

        remaining_attachments_count = (
            entry.attachments.count()
            - len(delete_attachment_ids)
            + len(attrs.get("attachments", []))
        )

        if not comment and remaining_attachments_count <= 0:
            raise serializers.ValidationError(
                "Запис щоденника не може бути порожнім."
            )

        return attrs