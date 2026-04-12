from django.db import models
from django.contrib.auth.models import User

from vendors.models import Vendor, VendorItem


class ExternalOrder(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        IN_PROGRESS = "in_progress", "В роботі"
        COMPLETED = "completed", "Виконано"
        CANCELLED = "cancelled", "Скасовано"

    order_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер замовлення",
    )

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Постачальник",
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        verbose_name="Статус",
    )

    prices_include_vat = models.BooleanField(
        default=False,
        verbose_name="Ціни включають ПДВ",
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Знижка",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, verbose_name="Коментар")

    image = models.FileField(
        upload_to="orders/",
        db_column="image_path",
        blank=True,
        null=True,
        verbose_name="Файл",
    )

    class Meta:
        db_table = "external_orders"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.order_no


class ExternalOrderItem(models.Model):
    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Замовлення",
    )

    vendor_item = models.ForeignKey(
        VendorItem,
        on_delete=models.PROTECT,
        verbose_name="Товар постачальника",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Кількість",
    )

    agreed_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        verbose_name="Ціна",
    )

    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Очікувана дата поставки",
    )

    class Meta:
        db_table = "external_order_items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.order} → {self.vendor_item}"


class ExternalPaymentDocument(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        APPROVED = "approved", "Погоджено"
        PAID = "paid", "Оплачено"
        CANCELLED = "cancelled", "Скасовано"

    payment_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер платіжного документа",
    )

    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.CASCADE,
        related_name="payment_documents",
        verbose_name="Замовлення",
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        verbose_name="Статус",
    )

    payment_amount = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        verbose_name="Сума оплати",
    )

    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата оплати",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_external_payment_documents",
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, verbose_name="Коментар")

    image = models.FileField(
        upload_to="payment_documents/",
        db_column="image_path",
        blank=True,
        null=True,
        verbose_name="Файл",
    )

    class Meta:
        db_table = "external_payment_documents"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.payment_no


class ExternalReceiptDocument(models.Model):
    receipt_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер документа приходу",
    )

    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.CASCADE,
        related_name="receipt_documents",
        verbose_name="Замовлення",
    )

    receipt_date = models.DateField(
        verbose_name="Дата приходу",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_external_receipt_documents",
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, verbose_name="Коментар")

    image = models.FileField(
        upload_to="receipt_documents/",
        db_column="image_path",
        blank=True,
        null=True,
        verbose_name="Файл",
    )

    class Meta:
        db_table = "external_receipt_documents"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.receipt_no


class ExternalReceiptItem(models.Model):
    receipt_document = models.ForeignKey(
        ExternalReceiptDocument,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Документ приходу",
    )

    order_item = models.ForeignKey(
        ExternalOrderItem,
        on_delete=models.PROTECT,
        related_name="receipt_items",
        verbose_name="Рядок замовлення",
    )

    received_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Отримана кількість",
    )

    class Meta:
        db_table = "external_receipt_items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.receipt_document} → {self.order_item}"