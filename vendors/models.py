from django.db import models
from reference.models import Brand, Country

class Vendor(models.Model):

    class TaxType(models.TextChoices):
        LLC_VAT = "LLC_VAT", "ТОВ / платник ПДВ"
        LLC_NO_VAT = "LLC_NO_VAT", "ТОВ / не платник ПДВ"
        FOP_2 = "FOP_2", "ФОП 2 група"
        FOP_3 = "FOP_3", "ФОП 3 група"
        NON_PROFIT = "NON_PROFIT", "Благодійна організація"

    code = models.CharField(max_length=50, unique=True, verbose_name="Код")
    name = models.CharField(max_length=255, verbose_name="Назва")
    legal_name = models.CharField(max_length=255, blank=True, verbose_name="Повна назва")

    tax_type = models.CharField(
        max_length=20,
        choices=TaxType.choices,
        verbose_name="Форма оподаткування"
    )

    edrpou = models.CharField(max_length=20, blank=True, verbose_name="ЄДРПОУ")
    ipn = models.CharField(max_length=20, blank=True, verbose_name="ІПН")

    phone = models.CharField(max_length=50, blank=True, verbose_name="Основний телефон")
    email = models.EmailField(blank=True, verbose_name="Основний e-mail")

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

    vendor_sku = models.CharField(max_length=100, blank=True)

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

    def __str__(self):
        return f"{self.vendor} → {self.item}"