import uuid

from django.db import models

def inv_item_image_upload_to(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    new_filename = f"{uuid.uuid4()}.{extension}" if extension else str(uuid.uuid4())
    return f"items/{new_filename}"


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
        upload_to=inv_item_image_upload_to,
        db_column="image_path",
        blank=True,
        null=True,
    )
    qr_item = models.BooleanField(default=False)
    requires_storage_place = models.BooleanField(default=True)
    is_splittable = models.BooleanField(default=False)
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
        
class Product(models.Model):
    product_family = models.ForeignKey(
        "ProductFamily",
        on_delete=models.PROTECT,
        db_column="product_family_id",
        related_name="products",
    )
    version = models.CharField(max_length=50)
    code = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    is_base_modification = models.BooleanField(default=False)
    development_started_at = models.DateField()
    development_finished_at = models.DateField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["product_family__name", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["product_family", "version"],
                name="uq_product_family_version",
            ),
            models.UniqueConstraint(
                fields=["product_family"],
                condition=models.Q(is_base_modification=True),
                name="uq_product_family_single_base_modification",
            ),
        ]

    def __str__(self):
        return f"{self.code}"


class ProductLibrary(models.Model):
    class AttachmentTypeChoices(models.TextChoices):
        PHOTO = "photo", "Фотографія"
        VIDEO = "video", "Відео"
        DRAWING = "drawing", "Креслення"
        DOCUMENTATION = "documentation", "Документація"

    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        db_column="product_id",
        related_name="library_items",
    )
    file = models.FileField(
        upload_to="product_library/",
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
        db_table = "product_library"
        ordering = ["name", "id"]

    def __str__(self):
        return f"{self.product.code} — {self.name}"

class ProductStep(models.Model):
    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        db_column="product_id",
        related_name="steps",
    )
    name = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField()

    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_steps"
        ordering = ["product", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "sort_order"],
                name="uq_product_step_product_sort_order",
            ),
            models.UniqueConstraint(
                fields=["product", "name"],
                name="uq_product_step_product_name",
            ),
        ]

    def __str__(self):
        return f"{self.product.code} — {self.sort_order}. {self.name}"


class ProductStepLibrary(models.Model):
    class AttachmentTypeChoices(models.TextChoices):
        PHOTO = "photo", "Фотографія"
        VIDEO = "video", "Відео"
        DRAWING = "drawing", "Креслення"
        DOCUMENTATION = "documentation", "Документація"

    product_step = models.ForeignKey(
        "ProductStep",
        on_delete=models.CASCADE,
        db_column="product_step_id",
        related_name="library_items",
    )
    file = models.FileField(
        upload_to="product_step_library/",
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
        db_table = "product_step_library"
        ordering = ["name", "id"]

    def __str__(self):
        return f"{self.product_step} — {self.name}"


class ProductStepItem(models.Model):
    product_step = models.ForeignKey(
        "ProductStep",
        on_delete=models.CASCADE,
        db_column="product_step_id",
        related_name="step_items",
    )
    inv_item = models.ForeignKey(
        "InvItem",
        on_delete=models.PROTECT,
        db_column="inv_item_id",
        related_name="product_step_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_step_items"
        ordering = ["product_step", "inv_item"]
        constraints = [
            models.UniqueConstraint(
                fields=["product_step", "inv_item"],
                name="uq_product_step_item_product_step_inv_item",
            ),
        ]

    def __str__(self):
        return f"{self.product_step} — {self.inv_item.name} ({self.quantity})"