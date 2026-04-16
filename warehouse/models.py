from django.db import models, transaction
from django.core.exceptions import ValidationError

class WarehouseLocation(models.Model):
    code = models.CharField(
        max_length=1,
        unique=True,
        editable=False,
        verbose_name="Код",
    )

    name = models.CharField(
        max_length=255,
        verbose_name="Назва",
    )

    address = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Адреса",
    )

    comment = models.TextField(
        blank=True,
        verbose_name="Коментар",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна",
    )

    class Meta:
        db_table = "warehouse_locations"
        ordering = ["code", "id"]
        verbose_name = "Локація складу"
        verbose_name_plural = "Локації складу"

    def __str__(self):
        return f"{self.code} — {self.name}"

    @staticmethod
    def _generate_next_code():
        existing_codes = set(
            WarehouseLocation.objects.select_for_update().values_list("code", flat=True)
        )

        for code_ord in range(ord("A"), ord("Z") + 1):
            candidate = chr(code_ord)
            if candidate not in existing_codes:
                return candidate

        raise ValueError("Вичерпано доступні коди локацій складу.")

    def save(self, *args, **kwargs):
        if not self.code:
            with transaction.atomic():
                self.code = self._generate_next_code()

        super().save(*args, **kwargs)


class WarehouseStoragePlace(models.Model):
    class PlaceType(models.TextChoices):
        CONTAINER = "container", "Контейнер"
        RACK = "rack", "Стелаж"
        BOX = "box", "Бокс"

    location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        related_name="storage_places",
        verbose_name="Локація",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
        verbose_name="Батьківське місце зберігання",
    )

    place_type = models.CharField(
        max_length=20,
        choices=PlaceType.choices,
        verbose_name="Тип місця зберігання",
    )

    code = models.CharField(
        max_length=3,
        unique=True,
        editable=False,
        verbose_name="Код",
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Назва",
    )

    comment = models.TextField(
        blank=True,
        verbose_name="Коментар",
    )

    qr_code = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        verbose_name="QR код",
    )

    image = models.ImageField(
        upload_to="warehouse/storage_places/",
        blank=True,
        null=True,
        verbose_name="Фото",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активне",
    )

    class Meta:
        db_table = "warehouse_storage_places"
        ordering = ["place_type", "code", "id"]
        verbose_name = "Місце зберігання"
        verbose_name_plural = "Місця зберігання"

    def __str__(self):
        return self.get_display_name()

    def get_display_name(self):
        parts = [self.location.code]

        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.append(current.code)
            current = current.parent

        parts.extend(reversed(ancestors))
        parts.append(self.code)

        return "-".join(parts)
        
    def clean(self):
        super().clean()

        if self.parent is not None and self.parent.location_id != self.location_id:
            raise ValidationError("Батьківське місце зберігання повинно бути в тій же локації.")

        if self.place_type == self.PlaceType.CONTAINER:
            if self.parent is not None:
                raise ValidationError("Контейнер може розміщуватися лише безпосередньо на локації.")

        elif self.place_type == self.PlaceType.RACK:
            if self.parent is not None and self.parent.place_type in [
                self.PlaceType.RACK,
                self.PlaceType.BOX,
            ]:
                raise ValidationError("Стелаж не може бути вкладений в інший стелаж або бокс.")

        elif self.place_type == self.PlaceType.BOX:
            pass
            
    def _get_code_width(self):
        if self.place_type in [self.PlaceType.CONTAINER, self.PlaceType.RACK]:
            return 2
        if self.place_type == self.PlaceType.BOX:
            return 3
        raise ValueError("Невідомий тип місця зберігання.")

    def _generate_next_code(self):
        width = self._get_code_width()

        last = (
            WarehouseStoragePlace.objects
            .select_for_update()
            .filter(place_type=self.place_type)
            .order_by("-code")
            .first()
        )

        if last is None:
            next_number = 1
        else:
            next_number = int(last.code) + 1

        return str(next_number).zfill(width)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        with transaction.atomic():
            if is_new and not self.code:
                self.code = self._generate_next_code()

            # генерация QR (жёстко связана с code)
            if not self.qr_code and self.code:
                self.qr_code = f"{self.place_type}:{self.code}"

            self.full_clean()
            super().save(*args, **kwargs)