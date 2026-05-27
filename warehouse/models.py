import os
import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.conf import settings

from inventory.models import InvItem
from orders.models import (
    ExternalOrderItem,
    ExternalReceiptItem,
    TollingOrderItem,
    TollingReceiptItem,
)
from sales.models import SalesOrder, SalesOrderComponent

def storage_place_image_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".bin"
    return f"warehouse/storage_places/{uuid.uuid4().hex}{ext}"


def storage_place_qr_pdf_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".pdf"
    return f"warehouse/storage_place_qr/{uuid.uuid4().hex}{ext}"


def movement_plan_invoice_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".pdf"
    return f"warehouse/movement_plan_invoices/{uuid.uuid4().hex}{ext}"


def production_movement_invoice_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".pdf"
    return f"warehouse/production_movement_invoices/{uuid.uuid4().hex}{ext}"
    
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

    qr_pdf_file = models.FileField(
        upload_to=storage_place_qr_pdf_upload_to,
        blank=True,
        null=True,
        verbose_name="QR PDF",
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
        visited_ids = {self.id} if self.id else set()
        current = self.parent
        while current is not None:
            if current.id in visited_ids:
                raise ValidationError("Виявлено циклічну вкладеність місць зберігання.")

            visited_ids.add(current.id)

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

    def get_display_name_verbose(self):
        chain = []
        visited_ids = set()
        current = self

        while current is not None:
            if current.id in visited_ids:
                raise ValidationError("Виявлено циклічну вкладеність місць зберігання.")

            visited_ids.add(current.id)

            chain.append(f"{current.get_place_type_display()} {current.code}")
            current = current.parent

        chain.reverse()
        result = ", ".join(chain)

        if self.parent is None:
            result = f"{result} на локації"

        return result

    def get_delete_block_reasons(self):
        reasons = []

        if self.children.exists():
            reasons.append("Є дочірні місця зберігання.")

        if self.warehouse_units.exists():
            reasons.append("Є складські одиниці.")

        if self.unit_events_from_storage_place.exists():
            reasons.append("Є складські події (джерело переміщення).")

        if self.unit_events_to_storage_place.exists():
            reasons.append("Є складські події (місце призначення).")

        if self.movement_plans.exists():
            reasons.append("Використовується в планах переміщення.")

        if self.executed_movement_plan_items_from_storage_place.exists():
            reasons.append("Використовується в виконаних переміщеннях.")

        return reasons

    def can_be_deleted(self):
        return len(self.get_delete_block_reasons()) == 0
        
    def clean(self):
        super().clean()

        if self.parent is not None and self.parent.location_id != self.location_id:
            raise ValidationError("Батьківське місце зберігання повинно бути в тій же локації.")

        if self.parent_id and self.parent_id == self.id:
            raise ValidationError("Місце зберігання не може бути власним батьком.")

        visited_ids = {self.id} if self.id else set()
        current = self.parent

        while current is not None:
            if current.id in visited_ids:
                raise ValidationError("Виявлено циклічну вкладеність місць зберігання.")

            visited_ids.add(current.id)
            current = current.parent

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

            self.full_clean()
            super().save(*args, **kwargs)


class WarehouseUnitEvent(models.Model):
    class OperationType(models.TextChoices):
        INTAKE = "intake", "Первинна прийомка"
        CONVERTED_INTAKE = "converted_intake", "Первинна прийомка з конвертацією"
        MOVE = "move", "Переміщення"
        SPLIT_MOVE = "split_move", "Переміщення з розділенням"
        PRODUCTION_TRANSFER = "production_transfer", "Передача у виробництво"
        PRODUCTION_CONSUME = "production_consume", "Використання у виробництві"
        RECLAMATION_RETURN = "reclamation_return", "Повернення постачальнику"

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

        if self.operation_type in [
            self.OperationType.PRODUCTION_TRANSFER,
            self.OperationType.RECLAMATION_RETURN,
        ]:
            if self.to_location is not None or self.to_storage_place is not None:
                raise ValidationError(
                    "Для цієї операції не потрібно вказувати to_location або to_storage_place."
                )
        elif (self.to_location is None) == (self.to_storage_place is None):
            raise ValidationError(
                "Потрібно вказати або to_location, або to_storage_place, але не обидва одночасно."
            )

        if self.operation_type in [
            self.OperationType.INTAKE,
            self.OperationType.CONVERTED_INTAKE,
        ]:
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
    class Status(models.TextChoices):
        ON_STOCK = "on_stock", "На складі"
        IN_PRODUCTION = "in_production", "У виробництві"
        CONSUMED = "consumed", "Використано"
        WRITTEN_OFF = "written_off", "Списано"
        RETURNED = "returned", "Повернено"
        BLOCKED = "blocked", "Заблоковано"

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
        null=True,
        blank=True,
        verbose_name="Джерело приходу",
    )

    source_order_item = models.ForeignKey(
        ExternalOrderItem,
        on_delete=models.PROTECT,
        related_name="warehouse_units",
        null=True,
        blank=True,
        verbose_name="Джерело рядка замовлення",
    )

    tolling_source_receipt_item = models.ForeignKey(
        TollingReceiptItem,
        on_delete=models.PROTECT,
        related_name="warehouse_units",
        null=True,
        blank=True,
        verbose_name="Джерело приходу (давальницька схема)",
    )

    tolling_source_order_item = models.ForeignKey(
        TollingOrderItem,
        on_delete=models.PROTECT,
        related_name="warehouse_units",
        null=True,
        blank=True,
        verbose_name="Джерело рядка замовлення (давальницька схема)",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ON_STOCK,
        verbose_name="Статус",
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

        if self.pk:
            from warehouse.models import MovementPlanItem

            if MovementPlanItem.objects.filter(
                warehouse_unit_id=self.pk,
                plan__status=MovementPlan.Status.ACTIVE,
            ).exists():
                raise ValidationError(
                    "Неможливо змінювати складську одиницю, яка зарезервована в активному плані переміщення."
                )

        if self.status in [
            self.Status.IN_PRODUCTION,
            self.Status.CONSUMED,
            self.Status.RETURNED,
        ]:
            if self.location is not None or self.storage_place is not None:
                raise ValidationError(
                    "Складська одиниця з цим статусом не повинна мати складську локацію або місце зберігання."
                )
        elif (self.location is None) == (self.storage_place is None):
            raise ValidationError(
                "Потрібно вказати або локацію, або місце зберігання, але не обидва одночасно."
            )

        if self.quantity <= 0:
            raise ValidationError({
                "quantity": "Кількість повинна бути більше 0."
            })

        procurement_used = bool(self.source_receipt_item_id or self.source_order_item_id)
        tolling_used = bool(
            self.tolling_source_receipt_item_id or self.tolling_source_order_item_id
        )

        if procurement_used and tolling_used:
            raise ValidationError(
                "Не можна одночасно використовувати procurement та давальницьке джерело."
            )

        if not procurement_used and not tolling_used:
            raise ValidationError(
                "Потрібно вказати джерело складської одиниці."
            )

        if procurement_used:
            if not self.source_receipt_item_id or not self.source_order_item_id:
                raise ValidationError(
                    "Для закупівлі потрібно вказати і джерело приходу, і рядок замовлення."
                )

            if self.source_receipt_item.order_item_id != self.source_order_item_id:
                raise ValidationError(
                    "Джерело приходу та рядок замовлення повинні збігатися."
                )

            if self.inventory_item_id != self.source_order_item.vendor_item.item_id:
                raise ValidationError(
                    "Номенклатура повинна збігатися з рядком замовлення."
                )

        if tolling_used:
            if (
                not self.tolling_source_receipt_item_id
                or not self.tolling_source_order_item_id
            ):
                raise ValidationError(
                    "Для давальницької схеми потрібно вказати і прихід, і рядок замовлення."
                )

            if (
                self.tolling_source_receipt_item.order_item_id
                != self.tolling_source_order_item_id
            ):
                raise ValidationError(
                    "Джерело приходу та рядок замовлення повинні збігатися."
                )

            if self.inventory_item_id != self.tolling_source_order_item.inv_item_id:
                raise ValidationError(
                    "Номенклатура повинна збігатися з рядком замовлення."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class WarehouseReceiptItemConversion(models.Model):
    receipt_item = models.OneToOneField(
        ExternalReceiptItem,
        on_delete=models.PROTECT,
        related_name="warehouse_conversion",
        verbose_name="Рядок приходу",
    )

    source_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Кількість у документах постачальника",
    )

    target_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Кількість у складських одиницях",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="warehouse_receipt_item_conversions",
        verbose_name="Хто створив",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Створено",
    )

    comment = models.TextField(
        blank=True,
        verbose_name="Коментар",
    )

    class Meta:
        db_table = "warehouse_receipt_item_conversions"
        ordering = ["-created_at", "-id"]
        verbose_name = "Конвертація рядка приходу"
        verbose_name_plural = "Конвертації рядків приходу"

    def __str__(self):
        return f"{self.receipt_item} → {self.target_quantity}"

    def clean(self):
        super().clean()

        if self.source_quantity <= 0:
            raise ValidationError({
                "source_quantity": "Кількість у документах повинна бути більше 0."
            })

        if self.target_quantity <= 0:
            raise ValidationError({
                "target_quantity": "Кількість для складу повинна бути більше 0."
            })

        if self.receipt_item_id:
            order_item = self.receipt_item.order_item
            receipt_document = self.receipt_item.receipt_document

            if not order_item.requires_unit_conversion:
                raise ValidationError(
                    "Конвертація дозволена лише для рядків, які потребують конвертації одиниць."
                )

            if not receipt_document.completed:
                raise ValidationError(
                    "Конвертація дозволена лише для завершеного документа приходу."
                )

            if receipt_document.sent_to_warehouse:
                raise ValidationError(
                    "Неможливо створити конвертацію для документа, вже переданого на склад."
                )

            if self.source_quantity != self.receipt_item.received_quantity:
                raise ValidationError({
                    "source_quantity": "Кількість у документах повинна збігатися з кількістю рядка приходу."
                })

            if self.receipt_item.warehouse_units.exists():
                raise ValidationError(
                    "Неможливо створити конвертацію для рядка, який вже оброблено складом."
                )

    def save(self, *args, **kwargs):
        if self.receipt_item_id:
            self.source_quantity = self.receipt_item.received_quantity

        self.full_clean()
        super().save(*args, **kwargs)


class MovementPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        ACTIVE = "active", "Активний"
        EXECUTED = "executed", "Виконаний"
        CANCELLED = "cancelled", "Скасований"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    target_location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movement_plans",
    )

    target_storage_place = models.ForeignKey(
        WarehouseStoragePlace,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movement_plans",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movement_plans",
        null=True,
        blank=True,
    )

    planned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    comment = models.TextField(
        blank=True,
    )

    invoice_file = models.FileField(
        upload_to=movement_plan_invoice_upload_to,
        blank=True,
        null=True,
    )

    invoice_generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    invoice_snapshot_hash = models.CharField(
        max_length=64,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "warehouse_movement_plans"

    def clean(self):
        if (self.target_location is None) == (self.target_storage_place is None):
            raise ValidationError(
                "Потрібно вказати або target_location, або target_storage_place, але не обидва одночасно."
            )


class WarehouseSalesOrderShortage(models.Model):
    inv_item = models.OneToOneField(
        InvItem,
        on_delete=models.PROTECT,
        related_name="warehouse_sales_order_shortage",
    )

    required_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    available_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    missing_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    last_recalculated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "warehouse_sales_order_shortages"
        ordering = ["inv_item__name", "inv_item_id"]

    def clean(self):
        super().clean()

        if self.required_quantity < 0:
            raise ValidationError({
                "required_quantity": "Потреба не може бути від'ємною."
            })

        if self.available_quantity < 0:
            raise ValidationError({
                "available_quantity": "Доступна кількість не може бути від'ємною."
            })

        if self.missing_quantity <= 0:
            raise ValidationError({
                "missing_quantity": "Кількість дефіциту повинна бути більше 0."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class WarehouseProductionReservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Зарезервовано"
        TRANSFERRED = "transferred", "Передано у виробництво"
        CANCELLED = "cancelled", "Скасовано"

    warehouse_unit = models.ForeignKey(
        WarehouseUnit,
        on_delete=models.PROTECT,
        related_name="production_reservations",
    )

    sales_order = models.ForeignKey(
        SalesOrder,
        on_delete=models.PROTECT,
        related_name="warehouse_production_reservations",
    )

    sales_order_component = models.ForeignKey(
        SalesOrderComponent,
        on_delete=models.PROTECT,
        related_name="warehouse_production_reservations",
    )

    production_order_step_component = models.ForeignKey(
        "production.ProductionOrderStepComponent",
        on_delete=models.PROTECT,
        related_name="warehouse_production_reservations",
        null=True,
        blank=True,
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="warehouse_production_reservations",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    transferred_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "warehouse_production_reservations"
        ordering = ["sales_order", "sales_order_component", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse_unit"],
                condition=models.Q(status="active"),
                name="uq_active_production_reservation_unit",
            ),
        ]

    def clean(self):
        super().clean()

        if self.quantity <= 0:
            raise ValidationError({
                "quantity": "Кількість повинна бути більше 0."
            })

        if (
            self.sales_order_component_id
            and self.sales_order_id
            and self.sales_order_component.sales_order_id != self.sales_order_id
        ):
            raise ValidationError(
                "Компонент повинен належати вказаному SalesOrder."
            )

        if (
            self.warehouse_unit_id
            and self.sales_order_component_id
            and self.warehouse_unit.inventory_item_id != self.sales_order_component.inv_item_id
        ):
            raise ValidationError(
                "Номенклатура WarehouseUnit повинна збігатися з компонентом SalesOrder."
            )

        if (
            self.production_order_step_component_id
            and self.sales_order_component_id
            and self.production_order_step_component.sales_order_component_id
            != self.sales_order_component_id
        ):
            raise ValidationError(
                "Компонент етапу повинен відповідати компоненту SalesOrder."
            )

        if (
            self.status == self.Status.ACTIVE
            and self.warehouse_unit_id
            and self.warehouse_unit.status != WarehouseUnit.Status.BLOCKED
        ):
            raise ValidationError(
                "Активний виробничий резерв повинен бути пов'язаний із WarehouseUnit у статусі blocked."
            )

        if (
            self.status == self.Status.ACTIVE
            and self.warehouse_unit_id
            and self.quantity > self.warehouse_unit.quantity
        ):
            raise ValidationError(
                "Кількість резерву не може перевищувати кількість WarehouseUnit."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class WarehouseProductionMovement(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Створено"
        EXECUTED = "executed", "Виконано"
        CANCELLED = "cancelled", "Скасовано"

    production_order = models.ForeignKey(
        "production.ProductionOrder",
        on_delete=models.PROTECT,
        related_name="warehouse_production_movements",
    )

    production_order_step = models.ForeignKey(
        "production.ProductionOrderStep",
        on_delete=models.PROTECT,
        related_name="warehouse_production_movements",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="warehouse_production_movements",
        null=True,
        blank=True,
    )

    issue_requested = models.BooleanField(
        default=False,
    )

    issue_requested_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    issue_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_warehouse_production_movements",
        null=True,
        blank=True,
    )

    comment = models.TextField(
        blank=True,
    )

    invoice_file = models.FileField(
        upload_to=production_movement_invoice_upload_to,
        blank=True,
        null=True,
    )

    invoice_generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    invoice_snapshot_hash = models.CharField(
        max_length=64,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    executed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "warehouse_production_movements"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["production_order_step"],
                condition=models.Q(status="created"),
                name="uq_created_production_movement_step",
            ),
        ]


class WarehouseProductionMovementItem(models.Model):
    movement = models.ForeignKey(
        WarehouseProductionMovement,
        on_delete=models.CASCADE,
        related_name="items",
    )

    production_reservation = models.ForeignKey(
        WarehouseProductionReservation,
        on_delete=models.PROTECT,
        related_name="production_movement_items",
    )

    source_warehouse_unit = models.ForeignKey(
        WarehouseUnit,
        on_delete=models.PROTECT,
        related_name="production_movement_source_items",
    )

    result_warehouse_unit = models.ForeignKey(
        WarehouseUnit,
        on_delete=models.PROTECT,
        related_name="production_movement_result_items",
        null=True,
        blank=True,
    )

    inventory_item = models.ForeignKey(
        InvItem,
        on_delete=models.PROTECT,
        related_name="production_movement_items",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    executed_source_location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        related_name="production_movement_items_from_location",
        null=True,
        blank=True,
    )

    executed_source_location_code = models.CharField(
        max_length=3,
        blank=True,
    )

    executed_source_location_name = models.CharField(
        max_length=255,
        blank=True,
    )

    executed_source_storage_place = models.ForeignKey(
        WarehouseStoragePlace,
        on_delete=models.PROTECT,
        related_name="production_movement_items_from_storage_place",
        null=True,
        blank=True,
    )

    executed_source_storage_place_code = models.CharField(
        max_length=3,
        blank=True,
    )

    executed_source_storage_place_display_name = models.CharField(
        max_length=255,
        blank=True,
    )

    executed_source_storage_place_full_display = models.CharField(
        max_length=500,
        blank=True,
    )

    class Meta:
        db_table = "warehouse_production_movement_items"
        ordering = ["movement", "inventory_item", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["production_reservation"],
                name="uq_production_movement_item_reservation",
            ),
        ]


class MovementPlanItem(models.Model):
    plan = models.ForeignKey(
        MovementPlan,
        on_delete=models.CASCADE,
        related_name="items",
    )

    warehouse_unit = models.ForeignKey(
        WarehouseUnit,
        on_delete=models.PROTECT,
        related_name="movement_plan_items",
    )

    reserved_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )

    move_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    remainder_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    requires_split = models.BooleanField(default=False)

    is_reserved = models.BooleanField(default=True)

    executed_source_location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        related_name="executed_movement_plan_items_from_location",
        null=True,
        blank=True,
    )

    executed_source_location_code = models.CharField(
        max_length=3,
        blank=True,
    )

    executed_source_location_name = models.CharField(
        max_length=255,
        blank=True,
    )

    executed_source_storage_place = models.ForeignKey(
        WarehouseStoragePlace,
        on_delete=models.PROTECT,
        related_name="executed_movement_plan_items_from_storage_place",
        null=True,
        blank=True,
    )

    executed_source_storage_place_code = models.CharField(
        max_length=3,
        blank=True,
    )

    executed_source_storage_place_display_name = models.CharField(
        max_length=255,
        blank=True,
    )

    executed_source_storage_place_full_display = models.CharField(
        max_length=500,
        blank=True,
    )

    class Meta:
        db_table = "warehouse_movement_plan_items"
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse_unit"],
                condition=models.Q(is_reserved=True),
                name="uq_reserved_movement_plan_unit",
            )
        ]