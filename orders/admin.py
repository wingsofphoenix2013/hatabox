from django.contrib import admin

from .models import (
    ExternalOrder,
    ExternalOrderEvent,
    ExternalOrderItem,
    TollingOrderEvent,
    ExternalPaymentDocument,
    ExternalRefundDocument,
    ExternalReceiptDocument,
    ExternalReceiptItem,
    TollingOrder,
    TollingOrderItem,
    TollingReceiptDocument,
    TollingReceiptItem,
    ReclamationReturnDocument,
    ReclamationReturnItem,
    ReclamationReturnDocumentLibrary,
    ReclamationReturnDocumentLibraryItem,
)


class ExternalOrderItemInline(admin.TabularInline):
    model = ExternalOrderItem
    extra = 0
    autocomplete_fields = ("vendor_item",)


@admin.register(ExternalOrderEvent)
class ExternalOrderEventAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "event_type",
        "source",
        "title",
        "created_by",
        "created_at",
    )
    search_fields = (
        "order__order_no",
        "title",
        "message",
        "created_by__username",
    )
    list_filter = (
        "event_type",
        "source",
        "created_by",
    )
    autocomplete_fields = ("order", "created_by")
    readonly_fields = (
        "order",
        "event_type",
        "source",
        "title",
        "message",
        "payload",
        "created_by",
        "created_at",
    )


@admin.register(ExternalOrder)
class ExternalOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_no",
        "vendor",
        "status",
        "prices_include_vat",
        "vat_amount",
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
        "requires_unit_conversion",
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
        "requires_unit_conversion",
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

@admin.register(ExternalRefundDocument)
class ExternalRefundDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "refund_no",
        "order",
        "refund_amount",
        "refund_date",
        "created_by",
        "created_at",
    )
    search_fields = (
        "refund_no",
        "order__order_no",
        "order__vendor__code",
        "order__vendor__name",
        "comment",
    )
    list_filter = (
        "refund_date",
        "order__vendor",
        "created_by",
    )
    autocomplete_fields = (
        "order",
        "created_by",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(ExternalReceiptDocument)
class ExternalReceiptDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_no",
        "order",
        "receipt_date",
        "completed",
        "sent_to_warehouse",
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
        "completed",
        "sent_to_warehouse",
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


class TollingOrderItemInline(admin.TabularInline):
    model = TollingOrderItem
    extra = 0
    autocomplete_fields = ("inv_item",)


@admin.register(TollingOrderEvent)
class TollingOrderEventAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "event_type",
        "source",
        "title",
        "created_by",
        "created_at",
    )
    search_fields = (
        "order__order_no",
        "title",
        "message",
        "created_by__username",
    )
    list_filter = (
        "event_type",
        "source",
        "created_by",
    )
    autocomplete_fields = ("order", "created_by")
    readonly_fields = (
        "order",
        "event_type",
        "source",
        "title",
        "message",
        "payload",
        "created_by",
        "created_at",
    )


@admin.register(TollingOrder)
class TollingOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_no",
        "organization",
        "status",
        "created_by",
        "created_at",
    )
    search_fields = (
        "order_no",
        "organization__name",
        "comment",
    )
    list_filter = (
        "status",
        "organization",
        "created_by",
    )
    autocomplete_fields = ("organization", "created_by")
    readonly_fields = ("created_at", "updated_at")
    inlines = [TollingOrderItemInline]


@admin.register(TollingOrderItem)
class TollingOrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "inv_item",
        "quantity",
        "requires_unit_conversion",
        "expected_delivery_date",
    )
    search_fields = (
        "order__order_no",
        "inv_item__internal_code",
        "inv_item__name",
    )
    list_filter = (
        "order__organization",
        "requires_unit_conversion",
    )
    autocomplete_fields = ("order", "inv_item")


class TollingReceiptItemInline(admin.TabularInline):
    model = TollingReceiptItem
    extra = 0
    autocomplete_fields = ("order_item",)


@admin.register(TollingReceiptDocument)
class TollingReceiptDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_no",
        "order",
        "receipt_date",
        "completed",
        "sent_to_warehouse",
        "created_by",
        "created_at",
    )
    search_fields = (
        "receipt_no",
        "order__order_no",
        "order__organization__name",
        "comment",
    )
    list_filter = (
        "receipt_date",
        "completed",
        "sent_to_warehouse",
        "order__organization",
        "created_by",
    )
    autocomplete_fields = ("order", "created_by")
    readonly_fields = ("created_at", "updated_at")
    inlines = [TollingReceiptItemInline]


@admin.register(TollingReceiptItem)
class TollingReceiptItemAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_document",
        "order_item",
        "received_quantity",
    )
    search_fields = (
        "receipt_document__receipt_no",
        "order_item__order__order_no",
        "order_item__inv_item__internal_code",
        "order_item__inv_item__name",
    )
    autocomplete_fields = ("receipt_document", "order_item")
    
class ReclamationReturnItemInline(admin.TabularInline):
    model = ReclamationReturnItem
    extra = 0
    autocomplete_fields = ("warehouse_unit",)


@admin.register(ReclamationReturnDocument)
class ReclamationReturnDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "return_no",
        "order",
        "status",
        "reason",
        "return_date",
        "created_by",
        "created_at",
    )
    search_fields = (
        "return_no",
        "order__order_no",
        "comment",
    )
    list_filter = (
        "status",
        "reason",
        "return_date",
        "created_by",
    )
    autocomplete_fields = (
        "order",
        "created_by",
    )
    inlines = (
        ReclamationReturnItemInline,
    )


@admin.register(ReclamationReturnItem)
class ReclamationReturnItemAdmin(admin.ModelAdmin):
    list_display = (
        "return_document",
        "warehouse_unit",
        "quantity",
    )
    autocomplete_fields = (
        "return_document",
        "warehouse_unit",
    )


class ReclamationReturnDocumentLibraryItemInline(admin.TabularInline):
    model = ReclamationReturnDocumentLibraryItem
    extra = 0


@admin.register(ReclamationReturnDocumentLibrary)
class ReclamationReturnDocumentLibraryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "return_document",
        "created_at",
    )
    search_fields = (
        "return_document__return_no",
        "return_document__order__order_no",
    )
    autocomplete_fields = (
        "return_document",
    )
    inlines = (
        ReclamationReturnDocumentLibraryItemInline,
    )


@admin.register(ReclamationReturnDocumentLibraryItem)
class ReclamationReturnDocumentLibraryItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "library",
        "attachment_type",
        "created_at",
    )
    list_filter = (
        "attachment_type",
    )
    autocomplete_fields = (
        "library",
    )