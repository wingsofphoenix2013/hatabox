from django.db import models


class Brand(models.Model):
    name = models.CharField("Бренд", max_length=255, unique=True)
    is_active = models.BooleanField("Активний", default=True)

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField("Країна", max_length=255, unique=True)
    code = models.CharField("Код ISO Alpha-3", max_length=3, unique=True)
    is_active = models.BooleanField("Активна", default=True)

    def __str__(self):
        return self.name
        
class ExternalOrderStatus(models.Model):
    code = models.CharField("Код", max_length=50, unique=True)
    name = models.CharField("Назва", max_length=255)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активний", default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Статус зовн. замовлення"
        verbose_name_plural = "Статуси зовн. замовлення"

    def __str__(self):
        return self.name
        
class ExternalOrderPaymentStatus(models.Model):
    code = models.CharField("Код", max_length=50, unique=True)
    name = models.CharField("Назва", max_length=255)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активний", default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Оплата зовн. замовлення"
        verbose_name_plural = "Оплата зовн. замовлення"

    def __str__(self):
        return self.name