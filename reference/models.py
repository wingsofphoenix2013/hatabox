from django.db import models


class Brand(models.Model):
    name = models.CharField("Бренд", max_length=255, unique=True)
    is_active = models.BooleanField("Активний", default=True)

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField("Країна", max_length=255, unique=True)
    code = models.CharField("Код", max_length=10, blank=True)
    is_active = models.BooleanField("Активна", default=True)

    def __str__(self):
        return self.name