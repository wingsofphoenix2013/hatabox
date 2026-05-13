from django.contrib import admin

from .models import (
    ProductionDiaryAttachment,
    ProductionDiaryEntry,
    ProductionOrder,
    ProductionOrderStep,
    ProductionOrderStepComponent,
)


class ProductionDiaryAttachmentInline(admin.TabularInline):
    model = ProductionDiaryAttachment
    extra = 0
    readonly_fields = (
        "created_at",
    )


class ProductionOrderStepComponentInline(admin.TabularInline):
    model = ProductionOrderStepComponent
    extra = 0
    autocomplete_fields = (
        "source_product_step_item",
        "sales_order_component",
        "inv_item",
    )
    readonly_fields = (
        "created_at",
    )


class ProductionOrderStepInline(admin.TabularInline):
    model = ProductionOrderStep
    extra = 0
    autocomplete_fields = (
        "source_product_step",
    )
    readonly_fields = (
        "created_at",
    )
    show_change_link = True


@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sales_order",
        "status",
        "serial_number",
        "use_work_tracking",
        "use_hr_tracking",
        "created_at",
        "ready_at",
    )
    list_filter = (
        "status",
        "use_work_tracking",
        "use_hr_tracking",
        "created_at",
        "ready_at",
    )
    search_fields = (
        "id",
        "sales_order__id",
        "serial_number",
        "comment",
    )
    autocomplete_fields = (
        "sales_order",
    )
    readonly_fields = (
        "created_at",
    )
    inlines = (
        ProductionOrderStepInline,
    )


@admin.register(ProductionOrderStep)
class ProductionOrderStepAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "production_order",
        "sequence_number",
        "name",
        "status",
        "started_at",
        "finished_at",
    )
    list_filter = (
        "status",
        "started_at",
        "finished_at",
    )
    search_fields = (
        "id",
        "production_order__id",
        "production_order__sales_order__id",
        "name",
    )
    autocomplete_fields = (
        "production_order",
        "source_product_step",
    )
    readonly_fields = (
        "created_at",
    )
    inlines = (
        ProductionOrderStepComponentInline,
    )


@admin.register(ProductionDiaryEntry)
class ProductionDiaryEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "production_order",
        "production_order_step",
        "author",
        "created_at",
    )
    list_filter = (
        "created_at",
        "author",
    )
    search_fields = (
        "id",
        "production_order__id",
        "production_order__sales_order__id",
        "production_order_step__name",
        "comment",
    )
    autocomplete_fields = (
        "production_order",
        "production_order_step",
        "author",
    )
    readonly_fields = (
        "created_at",
    )
    inlines = (
        ProductionDiaryAttachmentInline,
    )


@admin.register(ProductionDiaryAttachment)
class ProductionDiaryAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "entry",
        "attachment_type",
        "file",
        "created_at",
    )
    list_filter = (
        "attachment_type",
        "created_at",
    )
    search_fields = (
        "id",
        "entry__id",
        "entry__production_order__id",
        "entry__production_order__sales_order__id",
    )
    autocomplete_fields = (
        "entry",
    )
    readonly_fields = (
        "created_at",
    )


@admin.register(ProductionOrderStepComponent)
class ProductionOrderStepComponentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "production_order_step",
        "inv_item",
        "required_quantity",
        "is_required_for_step_start",
        "sales_order_component",
        "source_product_step_item",
        "created_at",
    )
    list_filter = (
        "is_required_for_step_start",
        "created_at",
    )
    search_fields = (
        "id",
        "production_order_step__production_order__id",
        "production_order_step__production_order__sales_order__id",
        "inv_item__internal_code",
        "inv_item__name",
    )
    autocomplete_fields = (
        "production_order_step",
        "source_product_step_item",
        "sales_order_component",
        "inv_item",
    )
    readonly_fields = (
        "created_at",
    )