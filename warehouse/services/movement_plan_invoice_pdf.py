from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from warehouse.services.movement_plan_invoice import build_movement_plan_invoice_snapshot


def generate_movement_plan_invoice_pdf(plan) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    y = height - 50

    # Заголовок
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Movement Plan #{plan.id}")
    y -= 30

    # Дата
    c.setFont("Helvetica", 10)
    if plan.planned_at:
        c.drawString(50, y, f"Planned at: {plan.planned_at}")
        y -= 20

    # Destination
    if plan.target_location:
        c.drawString(50, y, f"To location: {plan.target_location.code} - {plan.target_location.name}")
    elif plan.target_storage_place:
        sp = plan.target_storage_place
        c.drawString(50, y, f"To storage: {sp.get_display_name()}")
    y -= 30

    # Состав (source_lines snapshot)
    snapshot = build_movement_plan_invoice_snapshot(plan)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Items:")
    y -= 20

    c.setFont("Helvetica", 10)

    for row in snapshot:
        line = f"Item {row['inventory_item_id']} | Qty: {row['quantity']}"
        c.drawString(50, y, line)
        y -= 15

        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 50

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    return pdf