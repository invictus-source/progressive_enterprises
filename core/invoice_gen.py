"""
Progressive Enterprises – PDF Invoice Generator
Uses reportlab to generate professional A4 invoices.
"""

import os
import subprocess
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.colors import HexColor

import config


DARK_BLUE = HexColor("#1e3a5f")
ACCENT = HexColor("#2563eb")
LIGHT_GREY = HexColor("#f3f4f6")
MID_GREY = HexColor("#6b7280")
BLACK = HexColor("#111827")
WHITE = colors.white


def generate_invoice(sale) -> str:
    """
    Generate a PDF invoice for the given Sale ORM object.
    Returns the path to the saved PDF.
    """
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "invoices")
    os.makedirs(out_dir, exist_ok=True)
    filename = os.path.join(out_dir, f"{sale.invoice_no}.pdf")

    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle("Normal14", fontSize=9, textColor=BLACK, leading=13)
    bold_style = ParagraphStyle("Bold14", fontSize=10, fontName="Helvetica-Bold", textColor=BLACK)
    center_style = ParagraphStyle("Centered", alignment=TA_CENTER, fontSize=9)
    right_style = ParagraphStyle("Right", alignment=TA_RIGHT, fontSize=9)

    story = []

    # ── Header ────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f'<font size=18 color="#2563eb"><b>{config.COMPANY_NAME}</b></font>', styles["Normal"]),
        Paragraph(
            f'<font size=9 color="#6b7280">{config.COMPANY_ADDRESS}<br/>'
            f'📞 {config.COMPANY_PHONE}  |  ✉ {config.COMPANY_EMAIL}<br/>'
            f'GSTIN: {config.COMPANY_GSTIN}  |  State: {config.COMPANY_STATE} ({config.COMPANY_STATE_CODE})'
            f'</font>',
            right_style,
        ),
    ]]
    header_table = Table(header_data, colWidths=["50%", "50%"])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=4))

    # ── Invoice Meta ──────────────────────────────────────────────────────
    invoice_title = Paragraph('<font size=14 color="#2563eb"><b>TAX INVOICE</b></font>', center_style)
    story.append(invoice_title)
    story.append(Spacer(1, 4*mm))

    cust = sale.customer
    cust_info = f"{cust.name}<br/>{cust.phone}" if cust else "Walk-in Customer"
    if cust and cust.address:
        cust_info += f"<br/>{cust.address}"
    if cust and cust.gstin:
        cust_info += f"<br/>GSTIN: {cust.gstin}"

    meta_data = [
        [
            Paragraph(f'<b>Bill To:</b><br/>{cust_info}', normal),
            Paragraph(
                f'<b>Invoice No.:</b> {sale.invoice_no}<br/>'
                f'<b>Date:</b> {sale.sale_date.strftime("%d %B %Y")}<br/>'
                f'<b>Payment Mode:</b> {sale.payment_mode}',
                right_style,
            ),
        ]
    ]
    meta_table = Table(meta_data, colWidths=["55%", "45%"])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("BOX", (0, 0), (-1, -1), 0.5, MID_GREY),
        ("ROWPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 5*mm))

    # ── Items Table ───────────────────────────────────────────────────────
    items_header = ["#", "Product / Description", "HSN", "Qty", "Unit Price", "Disc%", "Taxable", "GST%", "GST Amt", "Total"]
    items_data = [items_header]
    for i, item in enumerate(sale.items, 1):
        from db.manager import get_db
        session = get_db()
        try:
            from db.models import Product
            p = session.query(Product).get(item.product_id)
            hsn = p.hsn_code if p else ""
        finally:
            session.close()
        items_data.append([
            str(i),
            item.product_name,
            hsn or "",
            str(item.qty),
            f"Rs. {item.unit_price:,.2f}",
            f"{item.discount_pct:.1f}%",
            f"Rs. {item.taxable_amount:,.2f}",
            f"{item.gst_rate:.0f}%",
            f"Rs. {item.gst_amount:,.2f}",
            f"Rs. {item.line_total:,.2f}",
        ])

    col_widths = [8*mm, 50*mm, 12*mm, 9*mm, 18*mm, 11*mm, 20*mm, 10*mm, 18*mm, 20*mm]
    items_table = Table(items_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 5*mm))

    # ── Totals ────────────────────────────────────────────────────────────
    totals_data = [
        ["", "Subtotal", f"Rs. {sale.subtotal:,.2f}"],
        ["", "Discount", f"Rs. {sale.discount_amount:,.2f}"],
        ["", "Taxable Amount", f"Rs. {sale.taxable_amount:,.2f}"],
        ["", "CGST", f"Rs. {sale.cgst_amount:,.2f}"],
        ["", "SGST", f"Rs. {sale.sgst_amount:,.2f}"],
        ["", "Total GST", f"Rs. {sale.total_gst:,.2f}"],
        ["", Paragraph('<b>GRAND TOTAL</b>', bold_style), Paragraph(f'<font size=12 color="#2563eb"><b>Rs. {sale.grand_total:,.2f}</b></font>', right_style)],
        ["", "Amount Received", f"Rs. {sale.amount_received:,.2f}"],
        ["", "Balance Due", f"Rs. {sale.balance_due:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=["55%", "25%", "20%"])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (1, 6), (-1, 6), 1, ACCENT),
        ("LINEBELOW", (1, 6), (-1, 6), 1, ACCENT),
        ("FONTNAME", (1, 6), (-1, 6), "Helvetica-Bold"),
        ("ROWPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 6*mm))

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        '<font size=8 color="#6b7280">This is a computer-generated invoice and does not require a physical signature. '
        'Goods once sold will not be taken back. Subject to local jurisdiction.<br/>'
        f'Thank you for shopping at {config.COMPANY_NAME}!</font>',
        center_style,
    ))

    doc.build(story)

    return filename
