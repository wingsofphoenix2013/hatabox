from django import forms
from django.contrib import admin

from .models import (
    MovementPlan,
    MovementPlanItem,
    WarehouseLocation,
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
        "is_active",
    )
    search_fields = (
        "inventory_item__internal_code",
        "inventory_item__name",
    )
    list_filter = (
        "is_active",
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