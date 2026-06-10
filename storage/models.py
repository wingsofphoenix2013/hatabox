from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class StorageLocation(models.Model):
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
        db_table = "storage_locations"
        ordering = ["code", "id"]
        verbose_name = "Локація зберігання"
        verbose_name_plural = "Локації зберігання"

    def __str__(self):
        return f"{self.code} — {self.name}"

    @staticmethod
    def _generate_next_code():
        existing_codes = set(
            StorageLocation.objects.select_for_update().values_list("code", flat=True)
        )

        for code_ord in range(ord("A"), ord("Z") + 1):
            candidate = chr(code_ord)
            if candidate not in existing_codes:
                return candidate

        raise ValueError("Вичерпано доступні коди локацій.")

    def clean(self):
        super().clean()

        if not self.pk:
            return

        original = StorageLocation.objects.get(pk=self.pk)

        if self.code != original.code:
            raise ValidationError({
                "code": "Код локації не можна змінювати після створення."
            })

        if self.address != original.address:
            raise ValidationError({
                "address": "Адресу локації не можна змінювати після створення."
            })

    def save(self, *args, **kwargs):
        if not self.code:
            with transaction.atomic():
                self.code = self._generate_next_code()

        self.full_clean()
        super().save(*args, **kwargs)


class StoragePlaceEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", "Створено"
        EDITED = "edited", "Відредаговано"
        MOVED = "moved", "Переміщено"
        ACTIVATED = "activated", "Активовано"
        DEACTIVATED = "deactivated", "Деактивовано"
        DEFAULT_CHANGED = "default_changed", "Змінено місце за замовчуванням"

    storage_place = models.ForeignKey(
        "StoragePlace",
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="Місце зберігання",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        verbose_name="Тип події",
    )

    payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Дані події",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="storage_place_events",
        null=True,
        blank=True,
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
        db_table = "storage_place_events"
        ordering = ["-created_at", "-id"]
        verbose_name = "Подія місця зберігання"
        verbose_name_plural = "Події місць зберігання"

    def __str__(self):
        return f"{self.get_event_type_display()} #{self.id}"


class StoragePlace(models.Model):
    class PlaceType(models.TextChoices):
        AREA = "area", "Площадка"
        CONTAINER = "container", "Контейнер"
        RACK = "rack", "Стелаж"
        SHELF = "shelf", "Полка"
        BOX = "box", "Коробка"

    location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="storage_places",
        null=True,
        blank=True,
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
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Код",
    )

    address = models.CharField(
        max_length=255,
        unique=True,
        editable=False,
        verbose_name="Адреса",
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

    is_active = models.BooleanField(
        default=False,
        verbose_name="Активне",
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="За замовчуванням",
    )

    class Meta:
        db_table = "storage_places"
        ordering = ["place_type", "code", "id"]
        verbose_name = "Місце зберігання"
        verbose_name_plural = "Місця зберігання"

    def __str__(self):
        return self.address or self.code

    def _get_code_prefix(self):
        mapping = {
            self.PlaceType.AREA: "Z",
            self.PlaceType.CONTAINER: "C",
            self.PlaceType.RACK: "R",
            self.PlaceType.SHELF: "S",
            self.PlaceType.BOX: "B",
        }
        return mapping[self.place_type]

    def _get_code_width(self):
        if self.place_type == self.PlaceType.BOX:
            return 3

        return 2

    def _generate_next_code(self):
        prefix = self._get_code_prefix()
        width = self._get_code_width()

        last = (
            StoragePlace.objects
            .select_for_update()
            .filter(
                place_type=self.place_type,
                code__startswith=prefix,
            )
            .order_by("-code")
            .first()
        )

        if last is None:
            next_number = 1
        else:
            next_number = int(last.code[1:]) + 1

        return f"{prefix}{str(next_number).zfill(width)}"

    def clean(self):
        super().clean()

        if (self.location is None) == (self.parent is None):
            raise ValidationError(
                "Потрібно вказати або location, або parent, але не обидва одночасно."
            )

        if self.parent_id and self.parent_id == self.id:
            raise ValidationError(
                "Місце зберігання не може бути власним батьком."
            )

        visited_ids = {self.id} if self.id else set()
        current = self.parent

        while current is not None:
            if current.id in visited_ids:
                raise ValidationError(
                    "Виявлено циклічну вкладеність місць зберігання."
                )

            visited_ids.add(current.id)
            current = current.parent

        if self.place_type == self.PlaceType.AREA:
            if self.parent is not None:
                raise ValidationError(
                    "Площадка може розміщуватися лише безпосередньо на локації."
                )

        elif self.place_type == self.PlaceType.CONTAINER:
            if self.parent is not None:
                raise ValidationError(
                    "Контейнер може розміщуватися лише безпосередньо на локації."
                )

        elif self.place_type == self.PlaceType.RACK:
            if (
                self.parent is not None
                and self.parent.place_type != self.PlaceType.CONTAINER
            ):
                raise ValidationError(
                    "Стелаж може розміщуватися лише на локації або в контейнері."
                )

        elif self.place_type == self.PlaceType.SHELF:
            if (
                self.parent is None
                or self.parent.place_type not in [
                    self.PlaceType.CONTAINER,
                    self.PlaceType.RACK,
                ]
            ):
                raise ValidationError(
                    "Полка може розміщуватися лише в контейнері або на стелажі."
                )

        elif self.place_type == self.PlaceType.BOX:
            if (
                self.parent is not None
                and self.parent.place_type == self.PlaceType.BOX
                and self.parent.parent is not None
                and self.parent.parent.place_type == self.PlaceType.BOX
            ):
                raise ValidationError(
                    "Коробка не може бути вкладена в коробку глибше одного рівня."
                )

        if self.pk:
            original = StoragePlace.objects.get(pk=self.pk)

            if (
                original.is_default
                and not self.is_default
                and not getattr(self, "_allow_unset_default", False)
            ):
                raise ValidationError({
                    "is_default": "Не можна зняти місце за замовчуванням напряму."
                })

        if self.is_default and self.place_type != self.PlaceType.AREA:
            raise ValidationError({
                "is_default": "Місцем за замовчуванням може бути лише площадка."
            })

        if self.is_default:
            root_location = self.get_root_location()

            existing_default = StoragePlace.objects.filter(
                is_default=True,
            ).exclude(
                pk=self.pk,
            )

            existing_default = [
                place for place in existing_default
                if place.get_root_location().id == root_location.id
            ]

            if existing_default:
                raise ValidationError({
                    "is_default": "На локації вже є місце зберігання за замовчуванням."
                })

        if self.is_active and not self.is_default:
            root_location = self.get_root_location()

            has_active_default = any(
                place.get_root_location().id == root_location.id
                for place in StoragePlace.objects.filter(
                    is_default=True,
                    is_active=True,
                    place_type=self.PlaceType.AREA,
                ).exclude(pk=self.pk)
            )

            if not has_active_default:
                raise ValidationError({
                    "is_active": "Неможливо активувати місце без активної площадки за замовчуванням на локації."
                })

    def get_root_location(self):
        current = self
        visited_ids = {self.id} if self.id else set()

        while current is not None:
            if current.location is not None:
                return current.location

            if current.parent_id in visited_ids:
                raise ValidationError("Виявлено циклічну вкладеність місць зберігання.")

            visited_ids.add(current.parent_id)
            current = current.parent

        raise ValidationError("Неможливо визначити кореневу локацію.")

    def _generate_address(self):
        parts = [self.code]

        current = self.parent
        visited_ids = {self.id} if self.id else set()
        root_location = self.location

        while current is not None:
            if current.id in visited_ids:
                raise ValidationError("Виявлено циклічну вкладеність місць зберігання.")

            visited_ids.add(current.id)
            parts.append(current.code)

            if current.location is not None:
                root_location = current.location
                break

            current = current.parent

        if root_location is None:
            raise ValidationError(
                "Неможливо сформувати адресу без кореневої локації."
            )

        parts.reverse()

        return "-".join([root_location.code] + parts)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        original_is_active = None
        original_editable_values = None

        if not is_new:
            original_editable_values = (
                StoragePlace.objects
                .filter(pk=self.pk)
                .values(
                    "name",
                    "comment",
                )
                .first()
            )
            original_is_active = (
                StoragePlace.objects
                .filter(pk=self.pk)
                .values_list("is_active", flat=True)
                .first()
            )

        if not self.code:
            with transaction.atomic():
                self.code = self._generate_next_code()

        if self.is_default:
            self.is_active = True

        self.address = self._generate_address()

        self.full_clean()
        super().save(*args, **kwargs)

        from storage.services.events import create_storage_place_event

        if is_new:
            create_storage_place_event(
                storage_place=self,
                event_type=StoragePlaceEvent.EventType.CREATED,
                payload={
                    "new": {
                        "location_id": self.location_id,
                        "parent_id": self.parent_id,
                        "place_type": self.place_type,
                        "code": self.code,
                        "address": self.address,
                        "name": self.name,
                        "comment": self.comment,
                        "is_active": self.is_active,
                        "is_default": self.is_default,
                    }
                },
            )

        elif original_is_active != self.is_active:
            create_storage_place_event(
                storage_place=self,
                event_type=(
                    StoragePlaceEvent.EventType.ACTIVATED
                    if self.is_active
                    else StoragePlaceEvent.EventType.DEACTIVATED
                ),
                payload={
                    "old": {
                        "is_active": original_is_active,
                    },
                    "new": {
                        "is_active": self.is_active,
                    },
                },
            )

        elif original_editable_values:
            changed = {}

            for field_name in [
                "name",
                "comment",
            ]:
                old_value = original_editable_values[field_name]
                new_value = getattr(self, field_name)

                if old_value != new_value:
                    changed[field_name] = {
                        "old": old_value,
                        "new": new_value,
                    }

            if changed:
                create_storage_place_event(
                    storage_place=self,
                    event_type=StoragePlaceEvent.EventType.EDITED,
                    payload={
                        "changed": changed,
                    },
                )