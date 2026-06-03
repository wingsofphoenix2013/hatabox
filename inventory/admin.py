from django.contrib import admin

from .models import (
    InvUnit,
    InvItemCategory,
    InvItem,
    ProductFamily,
    Product,
    ProductStep,
    ProductWork,
    ProductWorkItem,
    ProductStepItem,
)


@admin.register(InvUnit)
class InvUnitAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "symbol", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "symbol")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InvItemCategory)
class InvItemCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InvItem)
class InvItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "internal_code",
        "name",
        "category",
        "unit",
        "qr_item",
        "requires_storage_place",
        "is_splittable",
        "is_required_for_step_start",
        "is_active",
        "image",
    )
    list_filter = (
        "is_active",
        "qr_item",
        "requires_storage_place",
        "is_splittable",
        "is_required_for_step_start",
        "category",
        "unit",
    )
    search_fields = ("internal_code", "name", "description")
    autocomplete_fields = ("category", "unit")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "developer", "is_active")
    list_filter = ("developer", "is_active")
    search_fields = ("code", "name", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")

    
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "product_family",
        "version",
        "is_base_modification",
        "development_started_at",
        "development_finished_at",
        "is_active",
    )
    list_filter = (
        "is_base_modification",
        "is_active",
        "product_family",
    )
    search_fields = (
        "code",
        "version",
        "description",
        "product_family__code",
        "product_family__name",
    )
    autocomplete_fields = ("product_family",)
    ordering = ("product_family__name", "version")
    readonly_fields = ("created_at", "updated_at")


class ProductWorkItemInline(admin.TabularInline):
    model = ProductWorkItem
    extra = 0
    fields = (
        "inv_item",
        "quantity",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("inv_item",)
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


class ProductStepItemInline(admin.TabularInline):
    model = ProductStepItem
    extra = 0
    fields = (
        "inv_item",
        "quantity",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("inv_item",)
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


@admin.register(ProductStep)
class ProductStepAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "sort_order",
        "name",
        "created_at",
        "updated_at",
    )
    list_filter = ("product",)
    search_fields = (
        "name",
        "description",
        "product__code",
        "product__version",
        "product__product_family__code",
        "product__product_family__name",
    )
    autocomplete_fields = ("product",)
    ordering = ("product", "sort_order", "id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductStepItemInline]


@admin.register(ProductWork)
class ProductWorkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product_step",
        "sort_order",
        "name",
        "created_at",
        "updated_at",
    )
    list_filter = ("product_step",)
    search_fields = (
        "name",
        "description",
        "product_step__name",
        "product_step__product__code",
        "product_step__product__version",
    )
    autocomplete_fields = ("product_step",)
    ordering = ("product_step", "sort_order", "id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductWorkItemInline]


@admin.register(ProductWorkItem)
class ProductWorkItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product_work",
        "inv_item",
        "quantity",
        "created_at",
        "updated_at",
    )
    list_filter = ("product_work", "inv_item")
    search_fields = (
        "product_work__name",
        "product_work__product_step__name",
        "product_work__product_step__product__code",
        "product_work__product_step__product__version",
        "inv_item__internal_code",
        "inv_item__name",
    )
    autocomplete_fields = ("product_work", "inv_item")
    ordering = ("product_work", "inv_item")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductStepItem)
class ProductStepItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product_step",
        "inv_item",
        "quantity",
        "created_at",
        "updated_at",
    )
    list_filter = ("product_step", "inv_item")
    search_fields = (
        "product_step__name",
        "product_step__product__code",
        "product_step__product__version",
        "inv_item__internal_code",
        "inv_item__name",
    )
    autocomplete_fields = ("product_step", "inv_item")
    ordering = ("product_step", "inv_item")
    readonly_fields = ("created_at", "updated_at")