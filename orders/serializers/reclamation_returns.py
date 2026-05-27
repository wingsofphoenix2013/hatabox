from django.db import transaction

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

    order_item_id = serializers.IntegerField(
        source="order_item.id",
        read_only=True,
    )

    order_item_vendor_item_name = serializers.CharField(
        source="order_item.vendor_item.name",
        read_only=True,
    )

    class Meta:
        model = ReclamationReturnItem
        fields = [
            "id",
            "return_document",
            "order_item_id",
            "order_item_vendor_item_name",
            "warehouse_unit",
            "warehouse_unit_inventory_item_name",
            "warehouse_unit_inventory_item_code",
            "quantity",
            "source_location",
            "source_storage_place",
            "source_location_code",
            "source_location_name",
            "source_storage_place_code",
            "source_storage_place_display_name",
            "source_storage_place_full_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "quantity",
            "source_location",
            "source_storage_place",
            "source_location_code",
            "source_location_name",
            "source_storage_place_code",
            "source_storage_place_display_name",
            "source_storage_place_full_display",
            "created_at",
            "updated_at",
        )

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

        if warehouse_unit.status != warehouse_unit.Status.ON_STOCK:
            raise serializers.ValidationError(
                "Можна повертати лише складські одиниці у статусі 'На складі'."
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

    def create(self, validated_data):
        warehouse_unit = validated_data["warehouse_unit"]

        source_location = warehouse_unit.location
        source_storage_place = warehouse_unit.storage_place

        if source_storage_place is not None:
            source_location = source_storage_place.location

        with transaction.atomic():
            warehouse_unit.status = warehouse_unit.Status.BLOCKED
            warehouse_unit.save(update_fields=["status", "updated_at"])

            return super().create({
                **validated_data,
                "order_item": warehouse_unit.source_order_item,
                "quantity": warehouse_unit.quantity,
                "source_location": source_location,
                "source_storage_place": source_storage_place,
                "source_location_code": source_location.code if source_location else "",
                "source_location_name": source_location.name if source_location else "",
                "source_storage_place_code": source_storage_place.code if source_storage_place else "",
                "source_storage_place_display_name": (
                    source_storage_place.get_display_name()
                    if source_storage_place
                    else ""
                ),
                "source_storage_place_full_display": (
                    source_storage_place.get_display_name_verbose()
                    if source_storage_place
                    else ""
                ),
            })


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

    items = serializers.SerializerMethodField()

    library = serializers.SerializerMethodField()
    
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
            "library",
        ]
        read_only_fields = (
            "created_by",
            "created_at",
            "updated_at",
        )

    def get_items(self, obj):
        grouped = {}

        for item in obj.items.select_related(
            "order_item",
            "order_item__vendor_item",
            "order_item__vendor_item__item",
            "source_location",
            "source_storage_place",
        ):
            vendor_item = item.order_item.vendor_item
            inventory_item = vendor_item.item

            key = (
                item.order_item_id,
                inventory_item.id,
                item.source_location_id,
                item.source_storage_place_id,
            )

            if key not in grouped:
                grouped[key] = {
                    "order_item_id": item.order_item_id,
                    "vendor_item_id": vendor_item.id,
                    "vendor_item_name": vendor_item.name,
                    "inventory_item_id": inventory_item.id,
                    "inventory_item_code": inventory_item.internal_code,
                    "inventory_item_name": inventory_item.name,
                    "quantity": item.quantity,
                    "source_location": item.source_location_id,
                    "source_storage_place": item.source_storage_place_id,
                    "source_location_code": item.source_location_code,
                    "source_location_name": item.source_location_name,
                    "source_storage_place_code": item.source_storage_place_code,
                    "source_storage_place_display_name": item.source_storage_place_display_name,
                    "source_storage_place_full_display": item.source_storage_place_full_display,
                }
            else:
                grouped[key]["quantity"] += item.quantity

        return list(grouped.values())

    def get_library(self, obj):
        library = getattr(obj, "library", None)

        if library is None:
            return None

        return ReclamationReturnDocumentLibrarySerializer(library).data

    def validate(self, attrs):
        if (
            self.instance is not None
            and "status" in attrs
            and not self.context.get("allow_status_change")
        ):
            raise serializers.ValidationError({
                "status": "Статус рекламації змінюється лише через окрему дію."
            })

        return attrs


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
        
class ReclamationReturnCartItemSerializer(serializers.Serializer):
    order_item = serializers.IntegerField(min_value=1)

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
    )


class CreateReclamationReturnDocumentSerializer(serializers.Serializer):
    order = serializers.PrimaryKeyRelatedField(
        queryset=ReclamationReturnDocument._meta.get_field("order").remote_field.model.objects.all()
    )

    return_date = serializers.DateField()

    reason = serializers.ChoiceField(
        choices=ReclamationReturnDocument.ReasonChoices.choices,
    )

    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    items = ReclamationReturnCartItemSerializer(
        many=True,
        allow_empty=False,
    )
    
class ReclamationReturnAvailabilityItemSerializer(serializers.Serializer):
    order_item_id = serializers.IntegerField(read_only=True)
    vendor_item_id = serializers.IntegerField(read_only=True)
    vendor_item_name = serializers.CharField(read_only=True)
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)

    ordered_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    received_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    available_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    blocked_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    returned_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )