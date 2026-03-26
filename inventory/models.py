from django.db import models


class InvUnit(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "inv_units"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class InvItemCategory(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "inv_item_categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class InvItem(models.Model):
    internal_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    category = models.ForeignKey(
        "InvItemCategory",
        on_delete=models.PROTECT,
        db_column="category_id",
        related_name="items",
    )

    unit = models.ForeignKey(
        "InvUnit",
        on_delete=models.PROTECT,
        db_column="unit_id",
        related_name="items",
    )

    image_path = models.CharField(max_length=500, blank=True, null=True)
    qr_item = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "inv_items"
        ordering = ["name"]

    def __str__(self):
        return f"{self.internal_code} — {self.name}"