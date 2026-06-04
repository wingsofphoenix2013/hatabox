from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

from vendors.models import Vendor, VendorItem
from organizations.models import Organization
from inventory.models import InvItem


class ExternalOrder(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        IN_PROGRESS = "in_progress", "В роботі"
        COMPLETED = "completed", "Виконано"
        CANCELLED = "cancelled", "Скасовано"

    order_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер замовлення",
    )

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Постачальник",
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        verbose_name="Статус",
    )

    prices_include_vat = models.BooleanField(
        default=False,
        verbose_name="Ціни включають ПДВ",
    )

    vat_amount = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        verbose_name="Сума ПДВ",
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Знижка",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, verbose_name="Коментар")

    has_reclamation = models.BooleanField(
        default=False,
        verbose_name="Є рекламація",
    )

    image = models.FileField(
        upload_to="orders/",
        db_column="image_path",
        blank=True,
        null=True,
        verbose_name="Файл",
    )

    class Meta:
        db_table = "external_orders"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.order_no

class ExternalOrderEvent(models.Model):
    class Source(models.TextChoices):
        PROCUREMENT = "procurement", "Закупівля"
        LOGISTICS = "logistics", "Логістика"
        FINANCE = "finance", "Фінанси"
        SYSTEM = "system", "Система"

    class EventType(models.TextChoices):
        ORDER_CREATED = "order_created", "Замовлення створено"
        ORDER_STATUS_CHANGED = "order_status_changed", "Статус замовлення змінено"

        PAYMENT_DOCUMENT_CREATED = "payment_document_created", "Створено платіжний документ"
        PAYMENT_DOCUMENT_STATUS_CHANGED = "payment_document_status_changed", "Статус платіжного документа змінено"

        REFUND_DOCUMENT_CREATED = "refund_document_created", "Отримано повернення коштів"

        RECEIPT_DOCUMENT_CREATED = "receipt_document_created", "Створено документ приходу"
        RECEIPT_DOCUMENT_COMPLETED = "receipt_document_completed", "Документ приходу завершено"
        RECEIPT_DOCUMENT_SENT_TO_WAREHOUSE = "receipt_document_sent_to_warehouse", "Документ приходу передано на склад"

        RECLAMATION_RETURN_COMPLETED = "reclamation_return_completed", "Рекламацію завершено"

        COMMENT_ADDED = "comment_added", "Додано коментар"
        COMMENT_UPDATED = "comment_updated", "Оновлено коментар"
        COMMENT_DELETED = "comment_deleted", "Видалено коментар"

    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Замовлення",
    )

    event_type = models.CharField(
        max_length=64,
        choices=EventType.choices,
        verbose_name="Тип події",
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        verbose_name="Джерело",
    )

    title = models.CharField(
        max_length=255,
        verbose_name="Заголовок",
    )

    message = models.TextField(
        blank=True,
        verbose_name="Повідомлення",
    )

    payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Дані",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="external_order_events",
        null=True,
        blank=True,
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "external_order_events"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.order_id} — {self.event_type}"


class ExternalOrderItem(models.Model):
    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Замовлення",
    )

    vendor_item = models.ForeignKey(
        VendorItem,
        on_delete=models.PROTECT,
        verbose_name="Товар постачальника",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Кількість",
    )

    agreed_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        verbose_name="Ціна",
    )

    requires_unit_conversion = models.BooleanField(
        default=False,
        verbose_name="Потребує конвертації одиниць",
    )

    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Очікувана дата поставки",
    )

    class Meta:
        db_table = "external_order_items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.order} → {self.vendor_item}"

class ExternalPaymentDocument(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        APPROVED = "approved", "Погоджено"
        PAID = "paid", "Оплачено"
        CANCELLED = "cancelled", "Скасовано"

    payment_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер платіжного документа",
    )

    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.CASCADE,
        related_name="payment_documents",
        verbose_name="Замовлення",
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        verbose_name="Статус",
    )

    payment_amount = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        verbose_name="Сума оплати",
    )

    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата оплати",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_external_payment_documents",
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, verbose_name="Коментар")

    image = models.FileField(
        upload_to="payment_documents/",
        db_column="image_path",
        blank=True,
        null=True,
        verbose_name="Файл",
    )

    class Meta:
        db_table = "external_payment_documents"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.payment_no


class ExternalRefundDocument(models.Model):
    refund_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер документа повернення коштів",
    )

    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.CASCADE,
        related_name="refund_documents",
        verbose_name="Замовлення",
    )

    refund_amount = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        verbose_name="Сума повернення",
    )

    refund_date = models.DateField(
        verbose_name="Дата повернення коштів",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_external_refund_documents",
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    comment = models.TextField(
        blank=True,
        verbose_name="Коментар",
    )

    file = models.FileField(
        upload_to="refund_documents/",
        db_column="file_path",
        blank=True,
        null=True,
        verbose_name="Файл",
    )

    class Meta:
        db_table = "external_refund_documents"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.refund_no


class ExternalReceiptDocument(models.Model):
    receipt_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер документа приходу",
    )

    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.CASCADE,
        related_name="receipt_documents",
        verbose_name="Замовлення",
    )

    receipt_date = models.DateField(
        verbose_name="Дата приходу",
    )

    completed = models.BooleanField(
        default=False,
        verbose_name="Документ завершено",
    )

    sent_to_warehouse = models.BooleanField(
        default=False,
        verbose_name="Передано на склад",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_external_receipt_documents",
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, verbose_name="Коментар")

    image = models.FileField(
        upload_to="receipt_documents/",
        db_column="image_path",
        blank=True,
        null=True,
        verbose_name="Файл",
    )

    class Meta:
        db_table = "external_receipt_documents"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.receipt_no


class ExternalReceiptItem(models.Model):
    receipt_document = models.ForeignKey(
        ExternalReceiptDocument,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Документ приходу",
    )

    order_item = models.ForeignKey(
        ExternalOrderItem,
        on_delete=models.PROTECT,
        related_name="receipt_items",
        verbose_name="Рядок замовлення",
    )

    received_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Отримана кількість",
    )

    class Meta:
        db_table = "external_receipt_items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.receipt_document} → {self.order_item}"


class TollingOrder(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        ACTIVE = "active", "Активне"
        COMPLETED = "completed", "Виконано"

    order_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер замовлення",
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="tolling_orders",
        verbose_name="Організація",
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        verbose_name="Статус",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_tolling_orders",
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, verbose_name="Коментар")

    image = models.FileField(
        upload_to="tolling_orders/",
        db_column="image_path",
        blank=True,
        null=True,
        verbose_name="Файл",
    )

    class Meta:
        db_table = "tolling_orders"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.order_no


class TollingOrderEvent(models.Model):
    class Source(models.TextChoices):
        TOLLING = "tolling", "Давальницькі замовлення"
        LOGISTICS = "logistics", "Логістика"
        SYSTEM = "system", "Система"

    class EventType(models.TextChoices):
        ORDER_CREATED = "order_created", "Замовлення створено"
        ORDER_STATUS_CHANGED = "order_status_changed", "Статус замовлення змінено"

        RECEIPT_DOCUMENT_CREATED = "receipt_document_created", "Створено документ приходу"
        RECEIPT_DOCUMENT_COMPLETED = "receipt_document_completed", "Документ приходу завершено"
        RECEIPT_DOCUMENT_SENT_TO_WAREHOUSE = "receipt_document_sent_to_warehouse", "Документ приходу передано на склад"

        COMMENT_ADDED = "comment_added", "Додано коментар"
        COMMENT_UPDATED = "comment_updated", "Оновлено коментар"
        COMMENT_DELETED = "comment_deleted", "Видалено коментар"

    order = models.ForeignKey(
        TollingOrder,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Давальницьке замовлення",
    )

    event_type = models.CharField(
        max_length=64,
        choices=EventType.choices,
        verbose_name="Тип події",
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        verbose_name="Джерело",
    )

    title = models.CharField(
        max_length=255,
        verbose_name="Заголовок",
    )

    message = models.TextField(
        blank=True,
        verbose_name="Повідомлення",
    )

    payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Дані",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tolling_order_events",
        null=True,
        blank=True,
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tolling_order_events"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.order_id} — {self.event_type}"


class TollingOrderItem(models.Model):
    order = models.ForeignKey(
        TollingOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Замовлення",
    )

    inv_item = models.ForeignKey(
        InvItem,
        on_delete=models.PROTECT,
        related_name="tolling_order_items",
        verbose_name="Номенклатурна позиція",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Кількість",
    )

    requires_unit_conversion = models.BooleanField(
        default=False,
        verbose_name="Потребує конвертації одиниць",
    )

    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Очікувана дата поставки",
    )

    class Meta:
        db_table = "tolling_order_items"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "inv_item"],
                name="uq_tolling_order_item_order_inv_item",
            ),
        ]

    def __str__(self):
        return f"{self.order} → {self.inv_item}"


class TollingReceiptDocument(models.Model):
    receipt_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер документа приходу",
    )

    order = models.ForeignKey(
        TollingOrder,
        on_delete=models.CASCADE,
        related_name="receipt_documents",
        verbose_name="Замовлення",
    )

    receipt_date = models.DateField(
        verbose_name="Дата приходу",
    )

    completed = models.BooleanField(
        default=False,
        verbose_name="Документ завершено",
    )

    sent_to_warehouse = models.BooleanField(
        default=False,
        verbose_name="Передано на склад",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_tolling_receipt_documents",
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, verbose_name="Коментар")

    image = models.FileField(
        upload_to="tolling_receipt_documents/",
        db_column="image_path",
        blank=True,
        null=True,
        verbose_name="Файл",
    )

    class Meta:
        db_table = "tolling_receipt_documents"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.receipt_no


class TollingReceiptItem(models.Model):
    receipt_document = models.ForeignKey(
        TollingReceiptDocument,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Документ приходу",
    )

    order_item = models.ForeignKey(
        TollingOrderItem,
        on_delete=models.PROTECT,
        related_name="receipt_items",
        verbose_name="Рядок замовлення",
    )

    received_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Отримана кількість",
    )

    class Meta:
        db_table = "tolling_receipt_items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.receipt_document} → {self.order_item}"
        
class ReclamationReturnDocument(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        COMPLETED = "completed", "Завершено"
        CANCELLED = "cancelled", "Скасовано"

    class ReasonChoices(models.TextChoices):
        DEFECTIVE_PRODUCT = "defective_product", "Бракована продукція"
        PROCUREMENT_ERROR = "procurement_error", "Помилка у закупівлі"

    return_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер рекламації",
    )

    order = models.ForeignKey(
        ExternalOrder,
        on_delete=models.PROTECT,
        related_name="reclamation_returns",
        verbose_name="Замовлення",
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        verbose_name="Статус",
    )

    return_date = models.DateField(
        verbose_name="Дата повернення",
    )

    reason = models.CharField(
        max_length=30,
        choices=ReasonChoices.choices,
        verbose_name="Причина",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_reclamation_return_documents",
        verbose_name="Створено користувачем",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    comment = models.TextField(
        blank=True,
        verbose_name="Коментар",
    )

    class Meta:
        db_table = "reclamation_return_documents"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.return_no


class ReclamationReturnItem(models.Model):
    return_document = models.ForeignKey(
        ReclamationReturnDocument,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Документ рекламації",
    )

    order_item = models.ForeignKey(
        ExternalOrderItem,
        on_delete=models.PROTECT,
        related_name="reclamation_return_items",
        null=True,
        blank=True,
        verbose_name="Рядок замовлення",
    )

    warehouse_unit = models.ForeignKey(
        "warehouse.WarehouseUnit",
        on_delete=models.PROTECT,
        related_name="reclamation_return_items",
        verbose_name="Складська одиниця",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Кількість",
    )

    source_location = models.ForeignKey(
        "warehouse.WarehouseLocation",
        on_delete=models.PROTECT,
        related_name="reclamation_return_items",
        null=True,
        blank=True,
        verbose_name="Локація повернення",
    )

    source_storage_place = models.ForeignKey(
        "warehouse.WarehouseStoragePlace",
        on_delete=models.PROTECT,
        related_name="reclamation_return_items",
        null=True,
        blank=True,
        verbose_name="Місце зберігання повернення",
    )

    source_location_code = models.CharField(max_length=3, blank=True)
    source_location_name = models.CharField(max_length=255, blank=True)
    source_storage_place_code = models.CharField(max_length=3, blank=True)
    source_storage_place_display_name = models.CharField(max_length=255, blank=True)
    source_storage_place_full_display = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reclamation_return_items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.return_document} → {self.warehouse_unit}"


class ReclamationReturnDocumentLibrary(models.Model):
    return_document = models.OneToOneField(
        ReclamationReturnDocument,
        on_delete=models.CASCADE,
        related_name="library",
        verbose_name="Документ рекламації",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reclamation_return_document_libraries"


class ReclamationReturnDocumentLibraryItem(models.Model):
    class AttachmentTypeChoices(models.TextChoices):
        PHOTO = "photo", "Фотографія"
        VIDEO = "video", "Відео"

    library = models.ForeignKey(
        ReclamationReturnDocumentLibrary,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Бібліотека",
    )

    file = models.FileField(
        upload_to="reclamation_return_library/",
    )

    attachment_type = models.CharField(
        max_length=20,
        choices=AttachmentTypeChoices.choices,
        verbose_name="Тип вкладення",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reclamation_return_document_library_items"
        ordering = ["id"]