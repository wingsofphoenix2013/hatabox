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