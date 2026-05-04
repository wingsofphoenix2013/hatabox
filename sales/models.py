from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings

from organizations.models import Organization
from inventory.models import Product, InvItem


class SalesOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        CONFIRMED = "confirmed", "Підтверджено"
        IN_PROGRESS = "in_progress", "В роботі"
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

    comment = models.TextField(blank=True, verbose_name="Коментар")

    class Meta:
        db_table = "sales_orders"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.id} — {self.product}"


class SalesOrderComponent(models.Model):
    class SourceType(models.TextChoices):
        STOCK = "stock", "Склад"
        CUSTOMER = "customer", "Від замовника"
        DONATED = "donated", "Донорський"

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

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
    )

    source_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="provided_sales_order_components",
    )

    class Meta:
        db_table = "sales_order_components"
        ordering = ["sales_order", "id"]

    def clean(self):
        super().clean()

        if self.source_type == self.SourceType.CUSTOMER:
            self.source_organization = self.sales_order.organization

        if self.source_type == self.SourceType.STOCK:
            if self.source_organization is not None:
                raise ValidationError({
                    "source_organization": "Для джерела 'Склад' організація не вказується."
                })

        if self.source_type == self.SourceType.DONATED:
            if self.source_organization is None:
                raise ValidationError({
                    "source_organization": "Потрібно вказати організацію для цього джерела."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)