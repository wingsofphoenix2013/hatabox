from django.db import models, transaction
from django.core.exceptions import ValidationError
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
    vat = models.BooleanField(default=False, verbose_name="Платник ПДВ")
    website = models.URLField(blank=True, verbose_name="Сайт")
    logo = models.ImageField(
        upload_to="vendors/logos/",
        blank=True,
        null=True,
        verbose_name="Логотип"
    )

    is_active = models.BooleanField(default=True, verbose_name="Діючий")

    def __str__(self):
        return self.name

class VendorPaymentDetails(models.Model):
    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.PROTECT,
        related_name="payment_details",
        verbose_name="Постачальник",
    )

    label = models.CharField(max_length=255, verbose_name="Назва реквізитів")
    iban = models.CharField(max_length=29, verbose_name="IBAN")
    is_default = models.BooleanField(default=False, verbose_name="За замовчуванням")
    is_active = models.BooleanField(default=True, verbose_name="Діючі")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vendor", "iban"],
                name="uq_vendor_payment_details_vendor_iban",
            ),
            models.UniqueConstraint(
                fields=["vendor"],
                condition=models.Q(is_default=True),
                name="uq_vendor_payment_details_single_default",
            ),
        ]
        ordering = ["-is_default", "label", "id"]

    def __str__(self):
        return f"{self.vendor} — {self.label} — {self.iban}"

    def clean(self):
        super().clean()

        iban = self.iban.strip().upper()

        if len(iban) != 29:
            raise ValidationError({"iban": "IBAN must contain exactly 29 characters."})

        if not iban.startswith("UA"):
            raise ValidationError({"iban": "IBAN must start with 'UA'."})

        if not iban[2:].isdigit():
            raise ValidationError({"iban": "After 'UA', IBAN must contain only digits."})

        self.iban = iban

        if self.is_default and not self.is_active:
            raise ValidationError({
                "is_default": "Default payment details must be active."
            })

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not self.is_active:
            self.is_default = False

        with transaction.atomic():
            if is_new and not VendorPaymentDetails.objects.filter(vendor=self.vendor).exists():
                self.is_default = True

            if self.is_default:
                (
                    VendorPaymentDetails.objects
                    .select_for_update()
                    .filter(vendor=self.vendor)
                    .exclude(pk=self.pk)
                    .update(is_default=False)
                )

            self.full_clean()
            super().save(*args, **kwargs)

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