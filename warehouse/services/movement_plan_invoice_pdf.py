from weasyprint import HTML


def generate_movement_plan_invoice_pdf(plan) -> bytes:
    html = f"""
    <html>
        <body>
            <h1>Movement Plan #{plan.id}</h1>
            <p>Test WeasyPrint PDF</p>
        </body>
    </html>
    """

    pdf = HTML(string=html).write_pdf()
    return pdf