from django.db import models


class InvUnit(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    image = models.ImageField(
        upload_to="items/",
        db_column="image_path",
        blank=True,
        null=True,
    )
    qr_item = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inv_items"
        ordering = ["name"]

    def __str__(self):
        return f"{self.internal_code} — {self.name}"


class ProductFamily(models.Model):
    class DeveloperChoices(models.TextChoices):
        OWN = "own", "Власний"
        EXTERNAL = "external", "Зовнішній"

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    developer = models.CharField(
        max_length=20,
        choices=DeveloperChoices.choices,
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_families"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class ProductFamilyLibrary(models.Model):
    class AttachmentTypeChoices(models.TextChoices):
        PHOTO = "photo", "Фотографія"
        VIDEO = "video", "Відео"
        DRAWING = "drawing", "Креслення"
        DOCUMENTATION = "documentation", "Документація"

    product_family = models.ForeignKey(
        "ProductFamily",
        on_delete=models.CASCADE,
        db_column="product_family_id",
        related_name="library_items",
    )
    file = models.FileField(
        upload_to="product_family_library/",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    attachment_type = models.CharField(
        max_length=30,
        choices=AttachmentTypeChoices.choices,
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_family_library"
        ordering = ["name", "id"]

    def __str__(self):
        return f"{self.product_family.code} — {self.name}"