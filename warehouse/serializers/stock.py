from rest_framework import serializers


class WarehouseStockOverviewLocationSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


class WarehouseStockOverviewRowSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)

    inventory_item_category_id = serializers.IntegerField(read_only=True)
    inventory_item_category_name = serializers.CharField(read_only=True)

    inventory_item_unit_name = serializers.CharField(read_only=True)
    inventory_item_unit_symbol = serializers.CharField(read_only=True)

    available_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    reserved_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    pending_intake_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    procurement_pending_intake_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    tolling_pending_intake_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    incoming_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    has_procurement_pending_intake = serializers.BooleanField(read_only=True)
    has_tolling_pending_intake = serializers.BooleanField(read_only=True)
    has_unconverted_pending_intake = serializers.BooleanField(read_only=True)
    has_unconverted_incoming = serializers.BooleanField(read_only=True)

    locations = WarehouseStockOverviewLocationSerializer(
        many=True,
        read_only=True,
    )


class WarehouseStockOverviewQuerySerializer(serializers.Serializer):
    category = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )
    location = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )
    search = serializers.CharField(
        required=False,
        allow_blank=False,
    )

    has_stock = serializers.BooleanField(required=False)
    has_pending_intake = serializers.BooleanField(required=False)
    has_incoming = serializers.BooleanField(required=False)
    has_unconverted_pending_intake = serializers.BooleanField(required=False)
    has_unconverted_incoming = serializers.BooleanField(required=False)
    
class WarehouseStockDetailHeaderSerializer(serializers.Serializer):
    inventory_item_id = serializers.IntegerField(read_only=True)
    inventory_item_code = serializers.CharField(read_only=True)
    inventory_item_name = serializers.CharField(read_only=True)

    inventory_item_category_id = serializers.IntegerField(read_only=True)
    inventory_item_category_name = serializers.CharField(read_only=True)

    inventory_item_unit_id = serializers.IntegerField(read_only=True)
    inventory_item_unit_name = serializers.CharField(read_only=True)
    inventory_item_unit_symbol = serializers.CharField(read_only=True)

    image = serializers.CharField(read_only=True, allow_null=True)
    qr_item = serializers.CharField(read_only=True, allow_null=True)
    is_splittable = serializers.BooleanField(read_only=True)
    requires_storage_place = serializers.BooleanField(read_only=True)


class WarehouseStockDetailLocationSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


class WarehouseStockDetailSummarySerializer(serializers.Serializer):
    total_available_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    reserved_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    total_pending_intake_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    total_incoming_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    has_unconverted_pending_intake = serializers.BooleanField(read_only=True)
    has_unconverted_incoming = serializers.BooleanField(read_only=True)

    locations = WarehouseStockDetailLocationSerializer(
        many=True,
        read_only=True,
    )


class WarehouseStockDetailStockRowSerializer(serializers.Serializer):
    placement_type = serializers.CharField(read_only=True)

    location_id = serializers.IntegerField(read_only=True)
    location_code = serializers.CharField(read_only=True)
    location_name = serializers.CharField(read_only=True)

    storage_place_id = serializers.IntegerField(read_only=True, allow_null=True)
    storage_place_code = serializers.CharField(read_only=True, allow_null=True)
    storage_place_display_name = serializers.CharField(read_only=True, allow_null=True)
    storage_place_full_display = serializers.CharField(read_only=True, allow_null=True)

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )


class WarehouseStockDetailReservedStockRowSerializer(serializers.Serializer):
    placement_type = serializers.CharField(read_only=True)

    location_id = serializers.IntegerField(read_only=True)
    location_code = serializers.CharField(read_only=True)
    location_name = serializers.CharField(read_only=True)

    storage_place_id = serializers.IntegerField(read_only=True, allow_null=True)
    storage_place_code = serializers.CharField(read_only=True, allow_null=True)
    storage_place_display_name = serializers.CharField(read_only=True, allow_null=True)
    storage_place_full_display = serializers.CharField(read_only=True, allow_null=True)

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )

    movement_plan_id = serializers.IntegerField(read_only=True)
    movement_plan_status = serializers.CharField(read_only=True)
    movement_plan_planned_at = serializers.DateTimeField(read_only=True, allow_null=True)

    movement_plan_item_id = serializers.IntegerField(read_only=True)
    requires_split = serializers.BooleanField(read_only=True)
    move_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
        allow_null=True,
    )
    remainder_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
        allow_null=True,
    )


class WarehouseStockDetailPendingIntakeRowSerializer(serializers.Serializer):
    source_type = serializers.CharField(read_only=True)

    receipt_item_id = serializers.IntegerField(read_only=True)
    receipt_document_id = serializers.IntegerField(read_only=True)
    receipt_no = serializers.CharField(read_only=True)
    receipt_date = serializers.DateField(read_only=True)

    order_item_id = serializers.IntegerField(read_only=True)
    order_id = serializers.IntegerField(read_only=True)
    order_no = serializers.CharField(read_only=True)
    order_created_at = serializers.DateTimeField(read_only=True)

    counterparty_id = serializers.IntegerField(read_only=True)
    counterparty_name = serializers.CharField(read_only=True)

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    has_unconverted_quantity = serializers.BooleanField(read_only=True)


class WarehouseStockDetailIncomingRowSerializer(serializers.Serializer):
    source_type = serializers.CharField(read_only=True)

    order_item_id = serializers.IntegerField(read_only=True)
    order_id = serializers.IntegerField(read_only=True)
    order_no = serializers.CharField(read_only=True)
    order_created_at = serializers.DateTimeField(read_only=True)

    counterparty_id = serializers.IntegerField(read_only=True)
    counterparty_name = serializers.CharField(read_only=True)

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
    )
    has_unconverted_quantity = serializers.BooleanField(read_only=True)


class WarehouseStockDetailSerializer(serializers.Serializer):
    header = WarehouseStockDetailHeaderSerializer(read_only=True)
    summary = WarehouseStockDetailSummarySerializer(read_only=True)
    stock_rows = WarehouseStockDetailStockRowSerializer(
        many=True,
        read_only=True,
    )
    reserved_stock_rows = WarehouseStockDetailReservedStockRowSerializer(
        many=True,
        read_only=True,
    )
    pending_intake_rows = WarehouseStockDetailPendingIntakeRowSerializer(
        many=True,
        read_only=True,
    )
    incoming_rows = WarehouseStockDetailIncomingRowSerializer(
        many=True,
        read_only=True,
    )
