from django.contrib import admin

from sales.models import SalesOrder, SalesOrderComponent


class SalesOrderComponentInline(admin.TabularInline):
    model = SalesOrderComponent
    extra = 0
    autocomplete_fields = (
        "inv_item",
        "source_organization",
    )


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


@admin.register(SalesOrderComponent)
class SalesOrderComponentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sales_order",
        "inv_item",
        "quantity",
        "source_type",
        "source_organization",
    )
    list_filter = (
        "source_type",
        "source_organization",
    )
    search_fields = (
        "sales_order__id",
        "inv_item__internal_code",
        "inv_item__name",
        "source_organization__name",
    )
    autocomplete_fields = (
        "sales_order",
        "inv_item",
        "source_organization",
    )