from decimal import Decimal

from orders.models import (
    ExternalOrder,
    ExternalOrderEvent,
    ExternalPaymentDocument,
    ReclamationReturnDocument,
)
from orders.services.external_order_events import create_external_order_event


PAYMENT_COMPLETION_TOLERANCE = Decimal("0.01")


def get_external_order_financial_recovery_data(order):
    received_total_amount = Decimal("0.00")

    for item in order.items.all():
        received_quantity = Decimal("0.000")

        for receipt_item in item.receipt_items.select_related("receipt_document"):
            if receipt_item.receipt_document.completed:
                received_quantity += receipt_item.received_quantity

        capped_received_quantity = min(received_quantity, item.quantity)
        received_total_amount += capped_received_quantity * item.agreed_price

    reclamation_returned_amount = Decimal("0.00")

    for reclamation_return in order.reclamation_returns.all():
        if reclamation_return.status != ReclamationReturnDocument.StatusChoices.COMPLETED:
            continue

        for item in reclamation_return.items.select_related("order_item"):
            reclamation_returned_amount += item.quantity * item.order_item.agreed_price

    paid_amount = Decimal("0.00")

    for payment_document in order.payment_documents.all():
        if payment_document.status == ExternalPaymentDocument.StatusChoices.PAID:
            paid_amount += payment_document.payment_amount

    refunded_amount = Decimal("0.00")

    for refund_document in order.refund_documents.all():
        refunded_amount += refund_document.refund_amount

    net_paid_amount = paid_amount - refunded_amount
    effective_received_amount = received_total_amount - reclamation_returned_amount

    refund_possible_amount = (
        net_paid_amount
        - received_total_amount
        + reclamation_returned_amount
    )

    if refund_possible_amount <= PAYMENT_COMPLETION_TOLERANCE:
        refund_possible_amount = Decimal("0.00")

    return {
        "received_total_amount": received_total_amount,
        "reclamation_returned_amount": reclamation_returned_amount,
        "paid_amount": paid_amount,
        "refunded_amount": refunded_amount,
        "net_paid_amount": net_paid_amount,
        "effective_received_amount": effective_received_amount,
        "refund_possible_amount": refund_possible_amount,
    }


def recalculate_external_order_status_after_reclamation_or_refund(
    *,
    order,
    created_by=None,
):
    if order.status not in [
        ExternalOrder.StatusChoices.IN_PROGRESS,
        ExternalOrder.StatusChoices.COMPLETED,
    ]:
        return order

    data = get_external_order_financial_recovery_data(order)

    if data["refund_possible_amount"] > PAYMENT_COMPLETION_TOLERANCE:
        target_status = ExternalOrder.StatusChoices.IN_PROGRESS

    elif data["effective_received_amount"] <= PAYMENT_COMPLETION_TOLERANCE:
        target_status = ExternalOrder.StatusChoices.CANCELLED

    else:
        target_status = ExternalOrder.StatusChoices.COMPLETED

    if order.status == target_status:
        return order

    old_status = order.status
    order.status = target_status
    order.save(update_fields=["status"])

    create_external_order_event(
        order=order,
        event_type=ExternalOrderEvent.EventType.ORDER_STATUS_CHANGED,
        source=ExternalOrderEvent.Source.SYSTEM,
        title="Статус замовлення перераховано",
        payload={
            "from": old_status,
            "to": order.status,
            "reason": "reclamation_refund_recalculation",
            "received_total_amount": str(data["received_total_amount"]),
            "reclamation_returned_amount": str(data["reclamation_returned_amount"]),
            "paid_amount": str(data["paid_amount"]),
            "refunded_amount": str(data["refunded_amount"]),
            "net_paid_amount": str(data["net_paid_amount"]),
            "effective_received_amount": str(data["effective_received_amount"]),
            "refund_possible_amount": str(data["refund_possible_amount"]),
        },
        created_by=created_by,
    )

    return order