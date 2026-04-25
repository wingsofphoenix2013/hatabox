from orders.models import ExternalReceiptDocument, ExternalReceiptItem
from orders.models import TollingReceiptDocument, TollingReceiptItem


def mark_external_receipt_document_sent_if_fully_processed(receipt_document):
    remaining_items = ExternalReceiptItem.objects.filter(
        receipt_document=receipt_document,
    ).exclude(
        warehouse_units__is_active=True,
    ).distinct()

    if not remaining_items.exists():
        receipt_document.sent_to_warehouse = True
        receipt_document.save(update_fields=["sent_to_warehouse"])

    return receipt_document.sent_to_warehouse


def mark_external_receipt_document_sent_by_id_if_fully_processed(receipt_document_id):
    receipt_document = ExternalReceiptDocument.objects.get(id=receipt_document_id)
    return mark_external_receipt_document_sent_if_fully_processed(receipt_document)


def mark_tolling_receipt_document_sent_if_fully_processed(receipt_document):
    remaining_items = TollingReceiptItem.objects.filter(
        receipt_document=receipt_document,
    ).exclude(
        warehouse_units__is_active=True,
    ).distinct()

    if not remaining_items.exists():
        receipt_document.sent_to_warehouse = True
        receipt_document.save(update_fields=["sent_to_warehouse"])

    return receipt_document.sent_to_warehouse


def mark_tolling_receipt_document_sent_by_id_if_fully_processed(receipt_document_id):
    receipt_document = TollingReceiptDocument.objects.get(id=receipt_document_id)
    return mark_tolling_receipt_document_sent_if_fully_processed(receipt_document)