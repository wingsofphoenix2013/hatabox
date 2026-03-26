from django.contrib import admin

from .models import StaffDepartment, StaffPosition, StaffEmployee


@admin.register(StaffDepartment)
class StaffDepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("sort_order", "name")


@admin.register(StaffPosition)
class StaffPositionAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("sort_order", "name")


@admin.register(StaffEmployee)
class StaffEmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "last_name",
        "first_name",
        "middle_name",
        "department",
        "position",
        "is_active",
    )
    list_filter = ("is_active", "department", "position")
    search_fields = ("last_name", "first_name", "middle_name", "employee_no", "email", "phone")
    autocomplete_fields = ("department", "position", "user")
    ordering = ("last_name", "first_name")