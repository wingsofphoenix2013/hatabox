from django.contrib import admin
from django.utils import timezone

from .models import StaffDepartment, StaffPosition, StaffEmployee, StaffRole, StaffUserRole


@admin.register(StaffDepartment)
class StaffDepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_at:
            obj.created_at = timezone.now()
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(StaffPosition)
class StaffPositionAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_at:
            obj.created_at = timezone.now()
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(StaffRole)
class StaffRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_at:
            obj.created_at = timezone.now()
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(StaffUserRole)
class StaffUserRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "assigned_at", "assigned_by_user")
    list_filter = ("role",)
    search_fields = ("user__username", "role__code")
    autocomplete_fields = ("user", "role", "assigned_by_user")
    ordering = ("user", "role")
    readonly_fields = ("created_at", "assigned_at")

    def save_model(self, request, obj, form, change):
        from django.utils import timezone

        if not obj.assigned_at:
            obj.assigned_at = timezone.now()
        if not obj.created_at:
            obj.created_at = timezone.now()

        if not obj.assigned_by_user:
            obj.assigned_by_user = request.user

        super().save_model(request, obj, form, change)

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
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_at:
            obj.created_at = timezone.now()
        obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)