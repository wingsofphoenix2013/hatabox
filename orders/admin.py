from django.contrib import admin

from .models import (
    ExternalOrder,
    ExternalOrderItem,
    ExternalPaymentDocument,
    ExternalReceiptDocument,
    ExternalReceiptItem,
)


class ExternalOrderItemInline(admin.TabularInline):
    model = ExternalOrderItem
    extra = 0
    autocomplete_fields = ("vendor_item",)


@admin.register(ExternalOrder)
class ExternalOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_no",
        "vendor",
        "status",
        "prices_include_vat",
        "discount_amount",
        "created_by",
        "created_at",
    )
    search_fields = (
        "order_no",
        "vendor__code",
        "vendor__name",
        "comment",
    )
    list_filter = (
        "status",
        "prices_include_vat",
        "vendor",
        "created_by",
    )
    autocomplete_fields = ("vendor", "created_by")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ExternalOrderItemInline]


@admin.register(ExternalOrderItem)
class ExternalOrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "vendor_item",
        "quantity",
        "agreed_price",
        "expected_delivery_date",
    )
    search_fields = (
        "order__order_no",
        "vendor_item__vendor_sku",
        "vendor_item__name",
        "vendor_item__item__internal_code",
        "vendor_item__item__name",
    )
    list_filter = (
        "order__vendor",
    )
    autocomplete_fields = ("order", "vendor_item")


@admin.register(ExternalPaymentDocument)
class ExternalPaymentDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_no",
        "order",
        "status",
        "payment_amount",
        "payment_date",
        "created_by",
        "created_at",
    )
    search_fields = (
        "payment_no",
        "order__order_no",
        "order__vendor__code",
        "order__vendor__name",
        "comment",
    )
    list_filter = (
        "status",
        "payment_date",
        "order__vendor",
        "created_by",
    )
    autocomplete_fields = ("order", "created_by")
    readonly_fields = ("created_at", "updated_at")


class ExternalReceiptItemInline(admin.TabularInline):
    model = ExternalReceiptItem
    extra = 0
    autocomplete_fields = ("order_item",)


@admin.register(ExternalReceiptDocument)
class ExternalReceiptDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_no",
        "order",
        "receipt_date",
        "created_by",
        "created_at",
    )
    search_fields = (
        "receipt_no",
        "order__order_no",
        "order__vendor__code",
        "order__vendor__name",
        "comment",
    )
    list_filter = (
        "receipt_date",
        "order__vendor",
        "created_by",
    )
    autocomplete_fields = ("order", "created_by")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ExternalReceiptItemInline]


@admin.register(ExternalReceiptItem)
class ExternalReceiptItemAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_document",
        "order_item",
        "received_quantity",
    )
    search_fields = (
        "receipt_document__receipt_no",
        "order_item__order__order_no",
        "order_item__vendor_item__vendor_sku",
        "order_item__vendor_item__name",
        "order_item__vendor_item__item__internal_code",
        "order_item__vendor_item__item__name",
    )
    autocomplete_fields = ("receipt_document", "order_item")