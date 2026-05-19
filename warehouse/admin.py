from django import forms
from django.contrib import admin

from .models import (
    MovementPlan,
    MovementPlanItem,
    WarehouseLocation,
    WarehouseProductionMovement,
    WarehouseProductionMovementItem,
    WarehouseProductionReservation,
    WarehouseSalesOrderShortage,
    WarehouseStoragePlace,
    WarehouseUnit,
    WarehouseUnitEvent,
)

class WarehouseStoragePlaceAdminForm(forms.ModelForm):
    class Meta:
        model = WarehouseStoragePlace
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        location = None
        place_type = None

        if self.instance and self.instance.pk:
            location = self.instance.location
            place_type = self.instance.place_type

        data = self.data or None

        if data:
            location_id = data.get("location")
            place_type = data.get("place_type") or place_type

            if location_id:
                try:
                    location = WarehouseLocation.objects.get(pk=location_id)
                except WarehouseLocation.DoesNotExist:
                    location = None

        queryset = WarehouseStoragePlace.objects.none()

        if location is not None:
            queryset = WarehouseStoragePlace.objects.filter(
                location=location,
                is_active=True,
            )

            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)

        if place_type == WarehouseStoragePlace.PlaceType.CONTAINER:
            queryset = WarehouseStoragePlace.objects.none()

        elif place_type == WarehouseStoragePlace.PlaceType.RACK:
            queryset = queryset.exclude(
                place_type__in=[
                    WarehouseStoragePlace.PlaceType.RACK,
                    WarehouseStoragePlace.PlaceType.BOX,
                ]
            )

        elif place_type == WarehouseStoragePlace.PlaceType.BOX:
            pass

        self.fields["parent"].queryset = queryset

@admin.register(WarehouseLocation)
class WarehouseLocationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "address",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "address",
        "comment",
    )
    list_filter = (
        "is_active",
    )
    readonly_fields = (
        "code",
    )
    
@admin.register(WarehouseStoragePlace)
class WarehouseStoragePlaceAdmin(admin.ModelAdmin):
    form = WarehouseStoragePlaceAdminForm
    list_display = (
        "place_type",
        "code",
        "get_display_name",
        "location",
        "parent",
        "qr_pdf_file",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "comment",
    )
    list_filter = (
        "place_type",
        "location",
        "is_active",
    )
    autocomplete_fields = (
        "location",
        "parent",
    )
    readonly_fields = (
        "code",
    )

@admin.register(WarehouseUnit)
class WarehouseUnitAdmin(admin.ModelAdmin):
    list_display = (
        "inventory_item",
        "quantity",
        "location",
        "storage_place",
        "source_receipt_item",
        "source_order_item",
        "status",
    )
    search_fields = (
        "inventory_item__internal_code",
        "inventory_item__name",
    )
    list_filter = (
        "status",
        "inventory_item__unit",
        "location",
    )
    autocomplete_fields = (
        "inventory_item",
        "location",
        "storage_place",
        "source_receipt_item",
        "source_order_item",
    )
    
@admin.register(WarehouseUnitEvent)
class WarehouseUnitEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "operation_type",
        "source_unit",
        "result_unit",
        "quantity",
        "from_location",
        "from_storage_place",
        "to_location",
        "to_storage_place",
        "created_by",
        "created_at",
    )
    list_filter = ("operation_type", "created_at")
    search_fields = ("id",)
    
class MovementPlanItemInline(admin.TabularInline):
    model = MovementPlanItem
    extra = 0
    autocomplete_fields = (
        "warehouse_unit",
    )


@admin.register(MovementPlan)
class MovementPlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "target_location",
        "target_storage_place",
        "planned_at",
        "created_by",
        "created_at",
    )
    list_filter = (
        "status",
        "target_location",
        "target_storage_place",
        "planned_at",
        "created_at",
    )
    search_fields = (
        "id",
        "comment",
    )
    autocomplete_fields = (
        "target_location",
        "target_storage_place",
        "created_by",
    )
    inlines = (
        MovementPlanItemInline,
    )


@admin.register(WarehouseSalesOrderShortage)
class WarehouseSalesOrderShortageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "inv_item",
        "required_quantity",
        "available_quantity",
        "missing_quantity",
        "last_recalculated_at",
        "updated_at",
    )
    list_filter = (
        "updated_at",
    )
    search_fields = (
        "inv_item__internal_code",
        "inv_item__name",
    )
    autocomplete_fields = (
        "inv_item",
    )

class WarehouseProductionMovementItemInline(admin.TabularInline):
    model = WarehouseProductionMovementItem
    extra = 0
    autocomplete_fields = (
        "production_reservation",
        "source_warehouse_unit",
        "result_warehouse_unit",
        "inventory_item",
        "executed_source_location",
        "executed_source_storage_place",
    )


@admin.register(WarehouseProductionMovement)
class WarehouseProductionMovementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "production_order",
        "production_order_step",
        "status",
        "created_by",
        "created_at",
        "executed_at",
        "cancelled_at",
    )
    list_filter = (
        "status",
        "created_at",
        "executed_at",
        "cancelled_at",
    )
    search_fields = (
        "id",
        "production_order__id",
        "production_order_step__id",
        "production_order_step__name",
        "comment",
    )
    autocomplete_fields = (
        "production_order",
        "production_order_step",
        "created_by",
    )
    inlines = (
        WarehouseProductionMovementItemInline,
    )


@admin.register(WarehouseProductionMovementItem)
class WarehouseProductionMovementItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "movement",
        "production_reservation",
        "source_warehouse_unit",
        "result_warehouse_unit",
        "inventory_item",
        "quantity",
    )
    search_fields = (
        "id",
        "movement__id",
        "production_reservation__id",
        "source_warehouse_unit__id",
        "result_warehouse_unit__id",
        "inventory_item__internal_code",
        "inventory_item__name",
    )
    autocomplete_fields = (
        "movement",
        "production_reservation",
        "source_warehouse_unit",
        "result_warehouse_unit",
        "inventory_item",
        "executed_source_location",
        "executed_source_storage_place",
    )


@admin.register(WarehouseProductionReservation)
class WarehouseProductionReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "warehouse_unit",
        "sales_order",
        "sales_order_component",
        "quantity",
        "status",
        "created_by",
        "created_at",
        "transferred_at",
        "cancelled_at",
    )
    list_filter = (
        "status",
        "created_at",
        "transferred_at",
        "cancelled_at",
    )
    search_fields = (
        "id",
        "warehouse_unit__inventory_item__internal_code",
        "warehouse_unit__inventory_item__name",
        "sales_order__id",
        "sales_order_component__id",
    )
    autocomplete_fields = (
        "warehouse_unit",
        "sales_order",
        "sales_order_component",
        "created_by",
    )


@admin.register(MovementPlanItem)
class MovementPlanItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "plan",
        "warehouse_unit",
        "reserved_quantity",
        "move_quantity",
        "remainder_quantity",
        "requires_split",
        "is_reserved",
    )
    list_filter = (
        "requires_split",
        "is_reserved",
        "plan__status",
    )
    autocomplete_fields = (
        "plan",
        "warehouse_unit",
    )