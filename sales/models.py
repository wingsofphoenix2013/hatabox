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

    is_required_for_start = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "sales_order_components"
        ordering = ["sales_order", "id"]

    def clean(self):
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)