from django.contrib import admin

from sales.models import (
    SalesOrder,
    SalesOrderComponent,
    SalesOrderEvent,
)
from sales.services.orders import create_sales_order_components


class SalesOrderComponentInline(admin.TabularInline):
    model = SalesOrderComponent
    extra = 0
    autocomplete_fields = ()
    readonly_fields = ("inv_item", "quantity")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj and obj.status != obj.Status.DRAFT:
            return False
        return super().has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "product",
        "status",
        "created_by",
        "created_at",
    )
    list_filter = (
        "status",
        "organization",
        "product",
        "created_at",
    )
    search_fields = (
        "id",
        "organization__name",
        "product__code",
        "product__description",
        "comment",
    )
    autocomplete_fields = (
        "organization",
        "product",
        "created_by",
    )
    inlines = (
        SalesOrderComponentInline,
    )
    
    def save_model(self, request, obj, form, change):
        if obj.created_by_id is None:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)

        create_sales_order_components(obj)


@admin.register(SalesOrderComponent)
class SalesOrderComponentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sales_order",
        "inv_item",
        "quantity",
        "fulfillment_mode",
    )
    list_filter = (
        "fulfillment_mode",
    )
    search_fields = (
        "sales_order__id",
        "inv_item__internal_code",
        "inv_item__name",
    )
    autocomplete_fields = (
        "sales_order",
        "inv_item",
    )
    
@admin.register(SalesOrderEvent)
class SalesOrderEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sales_order",
        "event_type",
        "title",
        "created_by",
        "created_at",
    )

    list_filter = (
        "event_type",
        "created_at",
    )

    search_fields = (
        "sales_order__id",
        "title",
        "message",
    )

    autocomplete_fields = (
        "sales_order",
        "created_by",
    )

    readonly_fields = (
        "created_at",
    )