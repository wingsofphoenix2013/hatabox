from django.contrib import admin

from .models import (
    InvUnit,
    InvItemCategory,
    InvItem,
    ProductFamily,
    ProductFamilyLibrary,
    Product,
    ProductLibrary,
    ProductStep,
    ProductStepLibrary,
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
        "is_active",
        "image",
    )
    list_filter = ("is_active", "qr_item", "category", "unit")
    search_fields = ("internal_code", "name", "description")
    autocomplete_fields = ("category", "unit")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


class ProductFamilyLibraryInline(admin.TabularInline):
    model = ProductFamilyLibrary
    extra = 0
    fields = (
        "name",
        "attachment_type",
        "file",
        "is_active",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "developer", "is_active")
    list_filter = ("developer", "is_active")
    search_fields = ("code", "name", "description")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductFamilyLibraryInline]


@admin.register(ProductFamilyLibrary)
class ProductFamilyLibraryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "product_family",
        "attachment_type",
        "is_active",
        "file",
    )
    list_filter = ("attachment_type", "is_active", "product_family")
    search_fields = (
        "name",
        "description",
        "product_family__code",
        "product_family__name",
    )
    autocomplete_fields = ("product_family",)
    ordering = ("name", "id")
    readonly_fields = ("created_at", "updated_at")
    
class ProductLibraryInline(admin.TabularInline):
    model = ProductLibrary
    extra = 0
    fields = (
        "name",
        "attachment_type",
        "file",
        "is_active",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


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
    inlines = [ProductLibraryInline]


@admin.register(ProductLibrary)
class ProductLibraryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "product",
        "attachment_type",
        "is_active",
        "file",
    )
    list_filter = ("attachment_type", "is_active", "product")
    search_fields = (
        "name",
        "description",
        "product__code",
        "product__version",
        "product__product_family__code",
        "product__product_family__name",
    )
    autocomplete_fields = ("product",)
    ordering = ("name", "id")
    readonly_fields = ("created_at", "updated_at")
    
class ProductStepLibraryInline(admin.TabularInline):
    model = ProductStepLibrary
    extra = 0
    fields = (
        "name",
        "attachment_type",
        "file",
        "is_active",
        "created_at",
        "updated_at",
    )
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
        "product__code",
        "product__version",
        "product__product_family__code",
        "product__product_family__name",
    )
    autocomplete_fields = ("product",)
    ordering = ("product", "sort_order", "id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductStepLibraryInline, ProductStepItemInline]


@admin.register(ProductStepLibrary)
class ProductStepLibraryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "product_step",
        "attachment_type",
        "is_active",
        "file",
    )
    list_filter = ("attachment_type", "is_active", "product_step")
    search_fields = (
        "name",
        "description",
        "product_step__name",
        "product_step__product__code",
        "product_step__product__version",
        "product_step__product__product_family__code",
        "product_step__product__product_family__name",
    )
    autocomplete_fields = ("product_step",)
    ordering = ("name", "id")
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