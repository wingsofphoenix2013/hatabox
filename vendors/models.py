from django.db import models
from reference.models import Brand, Country, TaxType


class Vendor(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Код")
    name = models.CharField(max_length=255, verbose_name="Назва")
    legal_name = models.CharField(max_length=255, blank=True, verbose_name="Повна назва")

    tax_type = models.ForeignKey(
        TaxType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Форма оподаткування"
    )

    edrpou = models.CharField(max_length=20, blank=True, verbose_name="ЄДРПОУ")
    ipn = models.CharField(max_length=20, blank=True, verbose_name="ІПН")

    phone = models.CharField(max_length=50, blank=True, verbose_name="Основний телефон")
    email = models.EmailField(blank=True, verbose_name="Основний e-mail")
    logo = models.ImageField(
        upload_to="vendors/logos/",
        blank=True,
        null=True,
        verbose_name="Логотип"
    )

    is_active = models.BooleanField(default=True, verbose_name="Діючий")

    def __str__(self):
        return self.name


class VendorItem(models.Model):
    item = models.ForeignKey(
        "inventory.InvItem",
        on_delete=models.PROTECT,
        related_name="vendor_items"
    )

    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.PROTECT,
        related_name="vendor_items"
    )

    vendor_sku = models.CharField(max_length=100)
    name = models.CharField(max_length=255, verbose_name="Назва постачальника")

    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Бренд"
    )

    country_of_origin = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Країна походження"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vendor", "vendor_sku"],
                name="uq_vendor_item_vendor_vendor_sku",
            ),
        ]

    def __str__(self):
        return f"{self.vendor} → {self.vendor_sku} → {self.name}"