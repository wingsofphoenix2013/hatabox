from rest_framework import serializers

from orders.models import (
    ReclamationReturnDocument,
    ReclamationReturnItem,
    ReclamationReturnDocumentLibrary,
    ReclamationReturnDocumentLibraryItem,
)


class ReclamationReturnItemSerializer(serializers.ModelSerializer):
    warehouse_unit_inventory_item_name = serializers.CharField(
        source="warehouse_unit.inventory_item.name",
        read_only=True,
    )

    warehouse_unit_inventory_item_code = serializers.CharField(
        source="warehouse_unit.inventory_item.internal_code",
        read_only=True,
    )

    class Meta:
        model = ReclamationReturnItem
        fields = [
            "id",
            "return_document",
            "warehouse_unit",
            "warehouse_unit_inventory_item_name",
            "warehouse_unit_inventory_item_code",
            "quantity",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        return_document = attrs.get("return_document")
        warehouse_unit = attrs.get("warehouse_unit")

        if self.instance is not None:
            if return_document is None:
                return_document = self.instance.return_document

            if warehouse_unit is None:
                warehouse_unit = self.instance.warehouse_unit

        if return_document is None or warehouse_unit is None:
            return attrs

        if return_document.status != ReclamationReturnDocument.StatusChoices.DRAFT:
            raise serializers.ValidationError(
                "Можна змінювати рядки лише для рекламації у статусі 'Чернетка'."
            )

        if warehouse_unit.status == warehouse_unit.Status.RETURNED:
            raise serializers.ValidationError(
                "Складська одиниця вже повернена постачальнику."
            )

        if warehouse_unit.source_order_item_id is None:
            raise serializers.ValidationError(
                "Можна повертати лише procurement складські одиниці."
            )

        if warehouse_unit.source_order_item.order_id != return_document.order_id:
            raise serializers.ValidationError(
                "Складська одиниця повинна належати тому ж замовленню."
            )

        if warehouse_unit.outgoing_events.filter(
            operation_type=warehouse_unit.outgoing_events.model.OperationType.SPLIT_MOVE,
        ).exists():
            raise serializers.ValidationError(
                "Неможливо повернути складську одиницю, яка брала участь у split."
            )

        if warehouse_unit.incoming_events.filter(
            operation_type=warehouse_unit.incoming_events.model.OperationType.SPLIT_MOVE,
        ).exists():
            raise serializers.ValidationError(
                "Неможливо повернути складську одиницю, яка брала участь у split."
            )

        return attrs


class ReclamationReturnDocumentSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    reason_name = serializers.CharField(
        source="get_reason_display",
        read_only=True,
    )

    order_no = serializers.CharField(
        source="order.order_no",
        read_only=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    items = ReclamationReturnItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ReclamationReturnDocument
        fields = [
            "id",
            "return_no",
            "order",
            "order_no",
            "status",
            "status_name",
            "return_date",
            "reason",
            "reason_name",
            "comment",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = (
            "created_by",
            "created_at",
            "updated_at",
        )


class ReclamationReturnDocumentLibraryItemSerializer(serializers.ModelSerializer):
    attachment_type_name = serializers.CharField(
        source="get_attachment_type_display",
        read_only=True,
    )

    class Meta:
        model = ReclamationReturnDocumentLibraryItem
        fields = [
            "id",
            "library",
            "file",
            "attachment_type",
            "attachment_type_name",
            "created_at",
        ]
        read_only_fields = (
            "created_at",
        )


class ReclamationReturnDocumentLibrarySerializer(serializers.ModelSerializer):
    items = ReclamationReturnDocumentLibraryItemSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ReclamationReturnDocumentLibrary
        fields = [
            "id",
            "return_document",
            "created_at",
            "items",
        ]
        read_only_fields = (
            "created_at",
        )