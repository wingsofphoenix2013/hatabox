from django.db import models
from django.contrib.auth.models import User

from vendors.models import Vendor, VendorItem
from reference.models import (
    ExternalOrderStatus,
    ExternalOrderPaymentStatus,
)


class ExternalOrder(models.Model):
    order_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер замовлення"
    )

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Постачальник"
    )

    status = models.ForeignKey(
        ExternalOrderStatus,
        on_delete=models.PROTECT,
        verbose_name="Статус"
    )

    payment_status = models.ForeignKey(
        ExternalOrderPaymentStatus,
        on_delete=models.PROTECT,
        verbose_name="Статус оплати"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name="Створено користувачем"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    comment = models.TextField(blank=True, verbose_name="Коментар")

    is_active = models.BooleanField(default=True, verbose_name="Активний")

    def __str__(self):
        return self.order_no


class ExternalOrderItem(models.Model):
    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Замовлення"
    )

    vendor_item = models.ForeignKey(
        VendorItem,
        on_delete=models.PROTECT,
        verbose_name="Товар постачальника"
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Кількість"
    )

    agreed_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Ціна (UAH)"
    )

    lead_time_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Термін поставки (днів)"
    )

    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Очікувана дата поставки"
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.order} → {self.vendor_item}"