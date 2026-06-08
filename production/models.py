import os
import uuid

from django.db import models

from inventory.models import InvItem, ProductStep, ProductStepItem
from sales.models import SalesOrder, SalesOrderComponent


def production_diary_attachment_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".bin"
    return f"production/diary/{uuid.uuid4().hex}{ext}"


class ProductionOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        IN_PROGRESS = "in_progress", "В роботі"
        READY = "ready", "Готово"
        CANCELLED = "cancelled", "Скасовано"

    sales_order = models.OneToOneField(
        SalesOrder,
        on_delete=models.PROTECT,
        related_name="production_order",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    serial_number = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    use_work_tracking = models.BooleanField(
        default=False,
    )

    use_hr_tracking = models.BooleanField(
        default=False,
    )

    comment = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    expected_ready_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ready_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "production_orders"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.serial_number} — SalesOrder #{self.sales_order_id}"


class ProductionOrderStep(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        CONFIRMED = "confirmed", "Підтверджено"
        IN_PROGRESS = "in_progress", "В роботі"
        FINISHED = "finished", "Завершено"
        CANCELLED = "cancelled", "Скасовано"

    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    source_product_step = models.ForeignKey(
        ProductStep,
        on_delete=models.PROTECT,
        related_name="production_order_steps",
    )

    name = models.CharField(
        max_length=255,
    )

    sequence_number = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    expected_finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "production_order_steps"
        ordering = ["production_order", "sequence_number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["production_order", "sequence_number"],
                name="uq_production_order_step_sequence",
            ),
            models.UniqueConstraint(
                fields=["production_order", "source_product_step"],
                name="uq_production_order_step_source_product_step",
            ),
        ]

    def __str__(self):
        return f"{self.production_order_id} — {self.sequence_number}. {self.name}"


class ProductionDiaryEntry(models.Model):
    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="diary_entries",
    )

    production_order_step = models.ForeignKey(
        ProductionOrderStep,
        on_delete=models.SET_NULL,
        related_name="diary_entries",
        null=True,
        blank=True,
    )

    author = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="production_diary_entries",
    )

    comment = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "production_diary_entries"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"ProductionOrder #{self.production_order_id} — diary #{self.id}"


class ProductionDiaryAttachment(models.Model):
    class AttachmentType(models.TextChoices):
        PHOTO = "photo", "Фото"
        VIDEO = "video", "Відео"
        OTHER = "other", "Інше"

    entry = models.ForeignKey(
        ProductionDiaryEntry,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to=production_diary_attachment_upload_to,
    )

    attachment_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "production_diary_attachments"
        ordering = ["entry", "id"]

    def __str__(self):
        return f"DiaryEntry #{self.entry_id} — {self.attachment_type}"


class ProductionOrderMaterialSnapshot(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Очікує"
        PROCESSING = "processing", "Обробляється"
        COMPLETED = "completed", "Завершено"
        FAILED = "failed", "Помилка"

    production_order = models.OneToOneField(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="material_snapshot",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    calculated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "production_order_material_snapshots"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Material snapshot — ProductionOrder #{self.production_order_id}"


class ProductionOrderMaterialSnapshotItem(models.Model):
    class OriginType(models.TextChoices):
        OWN = "own", "Закупівля"
        CUSTOMER = "customer", "Замовник"
        DONOR = "donor", "Донор"

    snapshot = models.ForeignKey(
        ProductionOrderMaterialSnapshot,
        on_delete=models.CASCADE,
        related_name="items",
    )

    inv_item = models.ForeignKey(
        InvItem,
        on_delete=models.PROTECT,
        related_name="production_material_snapshot_items",
    )

    warehouse_unit = models.ForeignKey(
        "warehouse.WarehouseUnit",
        on_delete=models.PROTECT,
        related_name="production_material_snapshot_items",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    origin_type = models.CharField(
        max_length=20,
        choices=OriginType.choices,
    )

    source_order_item = models.ForeignKey(
        "orders.ExternalOrderItem",
        on_delete=models.PROTECT,
        related_name="production_material_snapshot_items",
        null=True,
        blank=True,
    )

    source_receipt_item = models.ForeignKey(
        "orders.ExternalReceiptItem",
        on_delete=models.PROTECT,
        related_name="production_material_snapshot_items",
        null=True,
        blank=True,
    )

    external_order = models.ForeignKey(
        "orders.ExternalOrder",
        on_delete=models.PROTECT,
        related_name="production_material_snapshot_items",
        null=True,
        blank=True,
    )

    external_order_no = models.CharField(
        max_length=50,
        blank=True,
    )

    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.PROTECT,
        related_name="production_material_snapshot_items",
        null=True,
        blank=True,
    )

    vendor_name = models.CharField(
        max_length=255,
        blank=True,
    )

    vendor_item = models.ForeignKey(
        "vendors.VendorItem",
        on_delete=models.PROTECT,
        related_name="production_material_snapshot_items",
        null=True,
        blank=True,
    )

    vendor_sku = models.CharField(
        max_length=100,
        blank=True,
    )

    prices_include_vat = models.BooleanField(
        null=True,
        blank=True,
    )

    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )

    cost_without_vat = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )

    vat_amount = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )

    cost_with_vat = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )

    tolling_source_order_item = models.ForeignKey(
        "orders.TollingOrderItem",
        on_delete=models.PROTECT,
        related_name="production_material_snapshot_items",
        null=True,
        blank=True,
    )

    tolling_source_receipt_item = models.ForeignKey(
        "orders.TollingReceiptItem",
        on_delete=models.PROTECT,
        related_name="production_material_snapshot_items",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "production_order_material_snapshot_items"
        ordering = ["snapshot", "inv_item", "id"]

    def __str__(self):
        return f"{self.snapshot_id} — {self.inv_item_id} ({self.quantity})"


class ProductionOrderStepComponent(models.Model):
    production_order_step = models.ForeignKey(
        ProductionOrderStep,
        on_delete=models.CASCADE,
        related_name="components",
    )

    source_product_step_item = models.ForeignKey(
        ProductStepItem,
        on_delete=models.PROTECT,
        related_name="production_order_step_components",
    )

    sales_order_component = models.ForeignKey(
        SalesOrderComponent,
        on_delete=models.PROTECT,
        related_name="production_order_step_components",
    )

    inv_item = models.ForeignKey(
        InvItem,
        on_delete=models.PROTECT,
        related_name="production_order_step_components",
    )

    required_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    is_required_for_step_start = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "production_order_step_components"
        ordering = [
            "production_order_step",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["production_order_step", "source_product_step_item"],
                name="uq_production_step_component_source_item",
            ),
        ]

    def __str__(self):
        return (
            f"{self.production_order_step_id} — "
            f"{self.inv_item} ({self.required_quantity})"
        )