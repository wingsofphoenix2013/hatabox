from django.db import models

from inventory.models import InvItem, ProductStep, ProductStepItem
from sales.models import SalesOrder, SalesOrderComponent


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