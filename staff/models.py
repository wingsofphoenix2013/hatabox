from django.db import models


class StaffDepartment(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "staff_departments"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class StaffPosition(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "staff_positions"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

  
class StaffEmployee(models.Model):
    employee_no = models.CharField(max_length=50, blank=True, null=True)

    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)

    birth_date = models.DateField(blank=True, null=True)

    department = models.ForeignKey(
        "StaffDepartment",
        on_delete=models.PROTECT,
        db_column="department_id",
        related_name="employees"
    )

    position = models.ForeignKey(
        "StaffPosition",
        on_delete=models.PROTECT,
        db_column="position_id",
        related_name="employees"
    )

    user = models.OneToOneField(
        "auth.User",
        on_delete=models.SET_NULL,
        db_column="user_id",
        blank=True,
        null=True,
        related_name="employee"
    )

    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)

    hire_date = models.DateField(blank=True, null=True)
    dismissal_date = models.DateField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "staff_employees"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.last_name} {self.first_name}"