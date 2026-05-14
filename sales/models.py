from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils import timezone

from organizations.models import Organization, Person
from inventory.models import Product, InvItem


class SalesOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        CONFIRMED = "confirmed", "Підтверджено"
        IN_PROGRESS = "in_progress", "В роботі"
        READY = "ready", "Готово до передачі"
        COMPLETED = "completed", "Виконано"
        CANCELLED = "cancelled", "Скасовано"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="sales_orders",
        verbose_name="Організація",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="sales_orders",
        verbose_name="Виріб",
    )

    customer_responsible_person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="responsible_sales_orders",
        verbose_name="Відповідальна особа замовника",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Статус",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_sales_orders",
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата виконання",
    )

    comment = models.TextField(blank=True, verbose_name="Коментар")

    class Meta:
        db_table = "sales_orders"
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        if self.status == self.Status.COMPLETED and self.completed_at is None:
            self.completed_at = timezone.now()

        if self.status != self.Status.COMPLETED:
            self.completed_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} — {self.product}"


class SalesOrderIssue(models.Model):
    class Stage(models.TextChoices):
        CONFIRMATION = "confirmation", "Підтвердження"
        PRODUCTION_START = "production_start", "Запуск виробництва"
        PRODUCTION_STEP_CONFIRMATION = "production_step_confirmation", "Підтвердження етапу"
        PRODUCTION_EXECUTION = "production_execution", "Виконання виробництва"

    class IssueType(models.TextChoices):
        CUSTOMER_COMPONENT_MISSING = (
            "customer_component_missing",
            "Відсутній товар замовника",
        )
        MIXED_COMPONENT_MISSING = (
            "mixed_component_missing",
            "Відсутній mixed-компонент",
        )
        STEP_COMPONENT_MISSING = (
            "step_component_missing",
            "Відсутній компонент етапу",
        )

    class Status(models.TextChoices):
        OPEN = "open", "Відкрита"
        RESOLVED = "resolved", "Вирішена"
        IGNORED = "ignored", "Проігнорована"

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Критична"
        NON_CRITICAL = "non_critical", "Некритична"

    sales_order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name="issues",
    )

    production_order = models.ForeignKey(
        "production.ProductionOrder",
        on_delete=models.CASCADE,
        related_name="issues",
        null=True,
        blank=True,
    )

    production_order_step = models.ForeignKey(
        "production.ProductionOrderStep",
        on_delete=models.CASCADE,
        related_name="issues",
        null=True,
        blank=True,
    )

    production_order_step_component = models.ForeignKey(
        "production.ProductionOrderStepComponent",
        on_delete=models.CASCADE,
        related_name="issues",
        null=True,
        blank=True,
    )

    stage = models.CharField(
        max_length=32,
        choices=Stage.choices,
    )

    issue_type = models.CharField(
        max_length=64,
        choices=IssueType.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
    )

    message = models.TextField(
        blank=True,
    )

    related_inv_item = models.ForeignKey(
        InvItem,
        on_delete=models.PROTECT,
        related_name="sales_order_issues",
        null=True,
        blank=True,
    )

    related_component = models.ForeignKey(
        "sales.SalesOrderComponent",
        on_delete=models.PROTECT,
        related_name="issues",
        null=True,
        blank=True,
    )

    missing_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_checked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "sales_order_issues"
        ordering = ["sales_order", "stage", "id"]

    def clean(self):
        super().clean()

        if (
            self.status == self.Status.IGNORED
            and self.severity == self.Severity.CRITICAL
        ):
            raise ValidationError(
                "Критичну проблему не можна проігнорувати."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SalesOrderComponent(models.Model):
    class FulfillmentMode(models.TextChoices):
        CUSTOMER = "customer", "Від замовника"
        MIXED = "mixed", "Комбіновано"

    sales_order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name="components",
    )

    inv_item = models.ForeignKey(
        InvItem,
        on_delete=models.PROTECT,
        related_name="sales_order_components",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    fulfillment_mode = models.CharField(
        max_length=20,
        choices=FulfillmentMode.choices,
        default=FulfillmentMode.MIXED,
    )

    class Meta:
        db_table = "sales_order_components"
        ordering = ["sales_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["sales_order", "inv_item"],
                name="uq_sales_order_component_sales_order_inv_item",
            ),
        ]

    def clean(self):
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
class SalesOrderEvent(models.Model):
    class Source(models.TextChoices):
        SALES = "sales", "Продажі"
        PRODUCTION = "production", "Виробництво"
        WAREHOUSE = "warehouse", "Склад"
        SYSTEM = "system", "Система"

    class EventType(models.TextChoices):
        SALES_ORDER_CREATED = (
            "sales_order_created",
            "SalesOrder створено",
        )

        SALES_ORDER_DETAILS_UPDATED = (
            "sales_order_details_updated",
            "Оновлено деталі SalesOrder",
        )

        SALES_ORDER_CONFIRMED = (
            "sales_order_confirmed",
            "SalesOrder підтверджено",
        )

        PRODUCTION_ORDER_CREATED = (
            "production_order_created",
            "Створено ProductionOrder",
        )

        SALES_ORDER_CANCELLED = (
            "sales_order_cancelled",
            "SalesOrder скасовано",
        )

        PRODUCTION_ORDER_CANCELLED = (
            "production_order_cancelled",
            "ProductionOrder скасовано",
        )

    sales_order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name="events",
    )

    event_type = models.CharField(
        max_length=64,
        choices=EventType.choices,
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField(
        blank=True,
    )

    payload = models.JSONField(
        default=dict,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales_order_events",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sales_order_events"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.sales_order_id} — {self.event_type}"