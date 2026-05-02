from rest_framework import serializers

from ..models import WarehouseStoragePlace


class WarehouseStoragePlaceStockRowSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)
    inventory_item_unit_symbol = serializers.CharField(read_only=True)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )


class WarehouseStoragePlaceNestedStockRowSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)
    inventory_item_unit_symbol = serializers.CharField(read_only=True)
    storage_place_id = serializers.IntegerField(read_only=True)
    storage_place_code = serializers.CharField(read_only=True)
    storage_place_display_name = serializers.CharField(read_only=True)
    storage_place_full_display = serializers.CharField(read_only=True)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )


class WarehouseStoragePlaceReservedStockRowSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)
    inventory_item_unit_symbol = serializers.CharField(read_only=True)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    movement_plan_id = serializers.IntegerField(read_only=True)
    movement_plan_status = serializers.CharField(read_only=True)
    movement_plan_planned_at = serializers.DateTimeField(read_only=True, allow_null=True)
    movement_plan_is_overdue = serializers.BooleanField(read_only=True)
    movement_plan_days_delta = serializers.IntegerField(read_only=True, allow_null=True)
    movement_plan_planned_status_text = serializers.CharField(read_only=True, allow_null=True)
    target_location_id = serializers.IntegerField(read_only=True)
    target_location_code = serializers.CharField(read_only=True)
    target_location_name = serializers.CharField(read_only=True)
    target_storage_place_id = serializers.IntegerField(read_only=True, allow_null=True)
    target_storage_place_code = serializers.CharField(read_only=True, allow_null=True)
    target_storage_place_display_name = serializers.CharField(read_only=True, allow_null=True)
    target_storage_place_full_display = serializers.CharField(read_only=True, allow_null=True)

class WarehouseStoragePlaceNestedReservedStockRowSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)
    inventory_item_unit_symbol = serializers.CharField(read_only=True)

    storage_place_id = serializers.IntegerField(read_only=True)
    storage_place_code = serializers.CharField(read_only=True)
    storage_place_display_name = serializers.CharField(read_only=True)
    storage_place_full_display = serializers.CharField(read_only=True)

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    movement_plan_id = serializers.IntegerField(read_only=True)
    movement_plan_status = serializers.CharField(read_only=True)
    movement_plan_planned_at = serializers.DateTimeField(read_only=True, allow_null=True)
    movement_plan_is_overdue = serializers.BooleanField(read_only=True)
    movement_plan_days_delta = serializers.IntegerField(read_only=True, allow_null=True)
    movement_plan_planned_status_text = serializers.CharField(read_only=True, allow_null=True)

    target_location_id = serializers.IntegerField(read_only=True)
    target_location_code = serializers.CharField(read_only=True)
    target_location_name = serializers.CharField(read_only=True)

    target_storage_place_id = serializers.IntegerField(read_only=True, allow_null=True)
    target_storage_place_code = serializers.CharField(read_only=True, allow_null=True)
    target_storage_place_display_name = serializers.CharField(read_only=True, allow_null=True)
    target_storage_place_full_display = serializers.CharField(read_only=True, allow_null=True)

class WarehouseStoragePlaceDetailSerializer(serializers.Serializer):
    storage_place = serializers.DictField(read_only=True)
    children = serializers.ListField(read_only=True)
    direct_stock = WarehouseStoragePlaceStockRowSerializer(
        many=True,
        read_only=True,
    )
    direct_reserved_stock = WarehouseStoragePlaceReservedStockRowSerializer(
        many=True,
        read_only=True,
    )
    nested_stock = WarehouseStoragePlaceNestedStockRowSerializer(
        many=True,
        read_only=True,
    )
    nested_reserved_stock = WarehouseStoragePlaceNestedReservedStockRowSerializer(
        many=True,
        read_only=True,
    )


class WarehouseStoragePlaceSerializer(serializers.ModelSerializer):
    location_code = serializers.CharField(source="location.code", read_only=True)
    parent_code = serializers.CharField(source="parent.code", read_only=True)
    parent_display_name = serializers.CharField(source="parent.get_display_name", read_only=True)
    place_type_name = serializers.CharField(source="get_place_type_display", read_only=True)
    display_name = serializers.CharField(source="get_display_name", read_only=True)
    placement_display = serializers.SerializerMethodField()
    display_name_verbose = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    delete_block_reasons = serializers.SerializerMethodField()

    class Meta:
        model = WarehouseStoragePlace
        fields = [
            "id",
            "location",
            "location_code",
            "parent",
            "parent_code",
            "parent_display_name",
            "place_type",
            "place_type_name",
            "code",
            "placement_display",
            "display_name_verbose",
            "name",
            "comment",
            "qr_pdf_file",
            "image",
            "is_active",
            "display_name",
            "can_delete",
            "delete_block_reasons",
        ]
        read_only_fields = ("code", "display_name")

    def get_placement_display(self, obj):
        if obj.parent is None:
            return "На локації"

        ancestors = []
        current = obj.parent

        while current is not None:
            ancestors.append(f"{current.get_place_type_display()} {current.code}")
            current = current.parent

        ancestors.reverse()
        return ", ".join(ancestors)
        
    def get_display_name_verbose(self, obj):
        return obj.get_display_name_verbose()
        
    def get_can_delete(self, obj):
        return obj.can_be_deleted()
        
    def get_delete_block_reasons(self, obj):
        return obj.get_delete_block_reasons()
