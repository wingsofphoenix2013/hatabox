from django.contrib import admin
from .models import ExternalOrder, ExternalOrderItem


class ExternalOrderItemInline(admin.TabularInline):
    model = ExternalOrderItem
    extra = 1


@admin.register(ExternalOrder)
class ExternalOrderAdmin(admin.ModelAdmin):
    list_display = ("order_no", "vendor", "status", "payment_status", "created_at")
    search_fields = ("order_no",)
    list_filter = ("status", "payment_status", "vendor")

    inlines = [ExternalOrderItemInline]


@admin.register(ExternalOrderItem)
class ExternalOrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "vendor_item", "quantity", "agreed_price")
    search_fields = ("order__order_no",)