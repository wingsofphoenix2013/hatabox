import os
import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.conf import settings

from inventory.models import InvItem
from orders.models import ExternalOrderItem, ExternalReceiptItem

def storage_place_image_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".bin"
    return f"warehouse/storage_places/{uuid.uuid4().hex}{ext}"
    
class WarehouseLocation(models.Model):
    code = models.CharField(
        max_length=3,
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
        upload_to=storage_place_image_upload_to,
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
        constraints = [
            models.UniqueConstraint(
                fields=["place_type", "code"],
                name="uq_warehouse_storage_place_type_code",
            ),
        ]

    def __str__(self):
        return self.get_display_name()

    def get_display_name(self):
        if not self.location_id or not self.code:
            return self.name or "Нове місце зберігання"

        ancestors = []
        current = self.parent
        while current is not None:
            if current.code and current.place_type:
                ancestors.append((current.place_type, current.code))
            current = current.parent

        ancestors = list(reversed(ancestors))

        parts = [self.location.code]

        for place_type, code in ancestors:
            if place_type == self.PlaceType.CONTAINER:
                parts[-1] = f"{parts[-1]}{code}"
            else:
                parts.append(code)

        if self.place_type == self.PlaceType.CONTAINER:
            parts[-1] = f"{parts[-1]}{self.code}"
        else:
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
        if self.place_type == self.PlaceType.CONTAINER:
            return 2
        if self.place_type == self.PlaceType.RACK:
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
            if self.place_type == self.PlaceType.RACK:
                next_number = int(last.code[1:]) + 1
            else:
                next_number = int(last.code) + 1

        if self.place_type == self.PlaceType.RACK:
            return f"R{str(next_number).zfill(width)}"

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

class WarehouseUnitEvent(models.Model):
    class OperationType(models.TextChoices):
        INTAKE = "intake", "Первинна прийомка"
        MOVE = "move", "Переміщення"
        SPLIT_MOVE = "split_move", "Переміщення з розділенням"

    operation_type = models.CharField(
        max_length=20,
        choices=OperationType.choices,
        verbose_name="Тип операції",
    )

    source_unit = models.ForeignKey(
        "WarehouseUnit",
        on_delete=models.PROTECT,
        related_name="outgoing_events",
        null=True,
        blank=True,
        verbose_name="Вихідна складська одиниця",
    )

    result_unit = models.ForeignKey(
        "WarehouseUnit",
        on_delete=models.PROTECT,
        related_name="incoming_events",
        verbose_name="Результуюча складська одиниця",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Кількість",
    )

    from_location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        related_name="unit_events_from_location",
        null=True,
        blank=True,
        verbose_name="Звідки: локація",
    )

    from_storage_place = models.ForeignKey(
        WarehouseStoragePlace,
        on_delete=models.PROTECT,
        related_name="unit_events_from_storage_place",
        null=True,
        blank=True,
        verbose_name="Звідки: місце зберігання",
    )

    to_location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        related_name="unit_events_to_location",
        null=True,
        blank=True,
        verbose_name="Куди: локація",
    )

    to_storage_place = models.ForeignKey(
        WarehouseStoragePlace,
        on_delete=models.PROTECT,
        related_name="unit_events_to_storage_place",
        null=True,
        blank=True,
        verbose_name="Куди: місце зберігання",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="warehouse_unit_events",
        null=True,
        blank=True,
        verbose_name="Хто створив",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Створено",
    )

    class Meta:
        db_table = "warehouse_unit_events"
        ordering = ["-created_at", "-id"]
        verbose_name = "Подія складської одиниці"
        verbose_name_plural = "Події складських одиниць"

    def __str__(self):
        return f"{self.get_operation_type_display()} #{self.id}"

    def clean(self):
        super().clean()

        if self.quantity <= 0:
            raise ValidationError({
                "quantity": "Кількість повинна бути більше 0."
            })

        if (self.to_location is None) == (self.to_storage_place is None):
            raise ValidationError(
                "Потрібно вказати або to_location, або to_storage_place, але не обидва одночасно."
            )

        if self.operation_type == self.OperationType.INTAKE:
            if self.source_unit is not None:
                raise ValidationError({
                    "source_unit": "Для первинної прийомки source_unit повинен бути порожнім."
                })

            if self.from_location is not None or self.from_storage_place is not None:
                raise ValidationError(
                    "Для первинної прийомки не потрібно вказувати from_location або from_storage_place."
                )

        else:
            if self.source_unit is None:
                raise ValidationError({
                    "source_unit": "Для цієї операції потрібно вказати source_unit."
                })

            if (self.from_location is None) == (self.from_storage_place is None):
                raise ValidationError(
                    "Потрібно вказати або from_location, або from_storage_place, але не обидва одночасно."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class WarehouseUnit(models.Model):
    inventory_item = models.ForeignKey(
        InvItem,
        on_delete=models.PROTECT,
        related_name="warehouse_units",
        verbose_name="Номенклатурна позиція",
    )

    location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        related_name="warehouse_units",
        null=True,
        blank=True,
        verbose_name="Локація",
    )

    storage_place = models.ForeignKey(
        WarehouseStoragePlace,
        on_delete=models.PROTECT,
        related_name="warehouse_units",
        null=True,
        blank=True,
        verbose_name="Місце зберігання",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Кількість",
    )

    source_receipt_item = models.ForeignKey(
        ExternalReceiptItem,
        on_delete=models.PROTECT,
        related_name="warehouse_units",
        verbose_name="Джерело приходу",
    )

    source_order_item = models.ForeignKey(
        ExternalOrderItem,
        on_delete=models.PROTECT,
        related_name="warehouse_units",
        verbose_name="Джерело рядка замовлення",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "warehouse_units"
        ordering = ["inventory_item__name", "id"]
        verbose_name = "Складська одиниця"
        verbose_name_plural = "Складські одиниці"

    def __str__(self):
        return f"{self.inventory_item} ({self.quantity})"

    def clean(self):
        super().clean()

        if (self.location is None) == (self.storage_place is None):
            raise ValidationError(
                "Потрібно вказати або локацію, або місце зберігання, але не обидва одночасно."
            )

        if self.quantity <= 0:
            raise ValidationError({
                "quantity": "Кількість повинна бути більше 0."
            })

        if self.source_receipt_item.order_item_id != self.source_order_item_id:
            raise ValidationError(
                "Джерело приходу та джерело рядка замовлення повинні посилатися на один і той самий рядок замовлення."
            )

        if self.inventory_item_id != self.source_order_item.vendor_item.item_id:
            raise ValidationError(
                "Номенклатурна позиція складської одиниці повинна збігатися з номенклатурою рядка замовлення."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)