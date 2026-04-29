from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from warehouse.serializers import MovementPlanSerializer


def generate_movement_plan_invoice_pdf(plan) -> bytes:
    serializer = MovementPlanSerializer(plan)
    data = serializer.data

    html = render_to_string(
        "warehouse/movement_plan_invoice.html",
        {
            "plan_id": plan.id,
            "invoice_generated_at": timezone.localtime(timezone.now()).strftime("%d.%m.%Y %H:%M"),
            "planned_at": (
                timezone.localtime(plan.planned_at).strftime("%d.%m.%Y %H:%M")
                if plan.planned_at
                else None
            ),
            "target_location_code": data["target_location_code"],
            "target_location_name": data["target_location_name"],
            "target_storage_place_full_display": data["target_storage_place_full_display"],
            "rows": data["source_lines"],
        },
    )

    pdf = HTML(string=html).write_pdf()
    return pdf