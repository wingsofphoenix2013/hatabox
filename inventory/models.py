import os
import uuid

from django.core.exceptions import ValidationError
from django.db import models

def inv_item_image_upload_to(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    new_filename = f"{uuid.uuid4()}.{extension}" if extension else str(uuid.uuid4())
    return f"items/{new_filename}"


def product_attachment_upload_to(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    new_filename = f"{uuid.uuid4()}.{extension}" if extension else str(uuid.uuid4())
    return f"product_attachments/{new_filename}"


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
    is_required_for_step_start = models.BooleanField(default=True)
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

        
class Product(models.Model):
    class DevelopmentStatus(models.TextChoices):
        IN_DEVELOPMENT = "in_development", "В розробці"
        FINISHED = "finished", "Розробку завершено"

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
    work_tracking = models.BooleanField(default=False)
    hr_tracking = models.BooleanField(default=False)
    development_status = models.CharField(
        max_length=30,
        choices=DevelopmentStatus.choices,
        default=DevelopmentStatus.IN_DEVELOPMENT,
    )
    development_started_at = models.DateField()
    development_finished_at = models.DateField(blank=True, null=True)
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


class ProductWork(models.Model):
    product_step = models.ForeignKey(
        "ProductStep",
        on_delete=models.CASCADE,
        db_column="product_step_id",
        related_name="works",
    )
    name = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField()
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_works"
        ordering = ["product_step", "sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product_step", "sort_order"],
                name="uq_product_work_product_step_sort_order",
            ),
            models.UniqueConstraint(
                fields=["product_step", "name"],
                name="uq_product_work_product_step_name",
            ),
        ]

    def __str__(self):
        return f"{self.product_step} — {self.sort_order}. {self.name}"


class ProductWorkItem(models.Model):
    product_work = models.ForeignKey(
        "ProductWork",
        on_delete=models.CASCADE,
        db_column="product_work_id",
        related_name="work_items",
    )
    inv_item = models.ForeignKey(
        "InvItem",
        on_delete=models.PROTECT,
        db_column="inv_item_id",
        related_name="product_work_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_work_items"
        ordering = ["product_work", "inv_item"]
        constraints = [
            models.UniqueConstraint(
                fields=["product_work", "inv_item"],
                name="uq_product_work_item_product_work_inv_item",
            ),
        ]

    def __str__(self):
        return f"{self.product_work} — {self.inv_item.name} ({self.quantity})"


class ProductAttachment(models.Model):
    class AttachmentTypeChoices(models.TextChoices):
        PHOTO = "photo", "Фотографія"
        VIDEO = "video", "Відео"
        DOCUMENT = "document", "Документ"
        DRAWING = "drawing", "Креслення"
        INSTRUCTION = "instruction", "Інструкція"
        OTHER = "other", "Інше"

    ALLOWED_FILE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".mp4",
        ".mov",
        ".avi",
        ".webm",
    }

    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )

    product_step = models.ForeignKey(
        "ProductStep",
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )

    product_work = models.ForeignKey(
        "ProductWork",
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )

    file = models.FileField(
        upload_to=product_attachment_upload_to,
    )

    display_filename = models.CharField(
        max_length=255,
        blank=True,
    )

    attachment_type = models.CharField(
        max_length=30,
        choices=AttachmentTypeChoices.choices,
    )

    is_primary_image = models.BooleanField(
        default=False,
    )

    name = models.CharField(
        max_length=255,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "product_attachments"
        ordering = ["-created_at", "-id"]

    def clean(self):
        super().clean()

        targets = [
            bool(self.product_id),
            bool(self.product_step_id),
            bool(self.product_work_id),
        ]

        if sum(targets) != 1:
            raise ValidationError(
                "Attachment must be linked to exactly one target."
            )

        if self.file:
            extension = os.path.splitext(self.file.name)[1].lower()

            if extension not in self.ALLOWED_FILE_EXTENSIONS:
                raise ValidationError({
                    "file": "Unsupported file type."
                })

        if (
            self.is_primary_image
            and self.attachment_type != self.AttachmentTypeChoices.PHOTO
        ):
            raise ValidationError({
                "is_primary_image": "Only photo attachments can be primary images."
            })

    def save(self, *args, **kwargs):
        if self.file and not self.display_filename:
            self.display_filename = os.path.basename(self.file.name)

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or self.file.name
        

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