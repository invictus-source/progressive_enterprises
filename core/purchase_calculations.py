"""Deterministic purchase-invoice calculations.

All arithmetic is performed with ``Decimal`` and rounded to paise using the
commercial half-up rule. UI code should use this module instead of duplicating
tax formulae.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


PAISE = Decimal("0.01")
RUPEE = Decimal("1")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(PAISE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PurchaseLineTotals:
    invoice_rate: Decimal
    basic_rate: Decimal
    gross_taxable: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    gst_amount: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class PurchaseInvoiceTotals:
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_gst: Decimal
    before_round_off: Decimal
    round_off: Decimal
    grand_total: Decimal


def calculate_purchase_line(
    *, qty: int, invoice_rate, discount_pct=0, gst_rate=18,
    tax_inclusive: bool = True, interstate: bool = False,
) -> PurchaseLineTotals:
    """Calculate one vendor invoice line.

    ``invoice_rate`` is the printed per-unit rate. For tax-inclusive invoices,
    GST is backed out before the line discount is applied, matching common
    Tally-style purchase invoices.
    """
    if int(qty) <= 0:
        raise ValueError("Quantity must be greater than zero.")
    rate = money(invoice_rate)
    discount = Decimal(str(discount_pct or 0))
    gst = Decimal(str(gst_rate or 0))
    if rate < 0:
        raise ValueError("Invoice rate cannot be negative.")
    if not Decimal("0") <= discount <= Decimal("100"):
        raise ValueError("Discount must be between 0 and 100%.")
    if not Decimal("0") <= gst <= Decimal("100"):
        raise ValueError("GST rate must be between 0 and 100%.")

    if tax_inclusive and gst:
        basic_rate = (rate * Decimal("100") / (Decimal("100") + gst)).quantize(
            PAISE, rounding=ROUND_HALF_UP
        )
    else:
        basic_rate = rate

    gross = money(basic_rate * int(qty))
    discount_amount = money(gross * discount / Decimal("100"))
    taxable = money(gross - discount_amount)

    if interstate:
        igst = money(taxable * gst / Decimal("100"))
        cgst = sgst = Decimal("0.00")
    else:
        half_rate = gst / Decimal("2")
        cgst = money(taxable * half_rate / Decimal("100"))
        sgst = money(taxable * half_rate / Decimal("100"))
        igst = Decimal("0.00")
    gst_amount = money(cgst + sgst + igst)

    return PurchaseLineTotals(
        invoice_rate=rate,
        basic_rate=basic_rate,
        gross_taxable=gross,
        discount_amount=discount_amount,
        taxable_amount=taxable,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        gst_amount=gst_amount,
        line_total=money(taxable + gst_amount),
    )


def calculate_purchase_invoice(lines, *, round_to_rupee: bool = True) -> PurchaseInvoiceTotals:
    lines = list(lines)
    subtotal = money(sum((x.gross_taxable for x in lines), Decimal("0")))
    discount = money(sum((x.discount_amount for x in lines), Decimal("0")))
    taxable = money(sum((x.taxable_amount for x in lines), Decimal("0")))
    cgst = money(sum((x.cgst_amount for x in lines), Decimal("0")))
    sgst = money(sum((x.sgst_amount for x in lines), Decimal("0")))
    igst = money(sum((x.igst_amount for x in lines), Decimal("0")))
    total_gst = money(cgst + sgst + igst)
    before_round = money(taxable + total_gst)
    grand = (
        before_round.quantize(RUPEE, rounding=ROUND_HALF_UP).quantize(PAISE)
        if round_to_rupee else before_round
    )
    return PurchaseInvoiceTotals(
        subtotal=subtotal,
        discount_amount=discount,
        taxable_amount=taxable,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        total_gst=total_gst,
        before_round_off=before_round,
        round_off=money(grand - before_round),
        grand_total=grand,
    )
