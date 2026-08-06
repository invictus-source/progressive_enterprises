import unittest
from decimal import Decimal

from core.purchase_calculations import calculate_purchase_invoice, calculate_purchase_line


class PurchaseCalculationTests(unittest.TestCase):
    def test_sample_vendor_invoice_matches_to_the_paise(self):
        battery = calculate_purchase_line(
            qty=2, invoice_rate="17379", discount_pct="5",
            gst_rate="18", tax_inclusive=True,
        )
        inverter = calculate_purchase_line(
            qty=2, invoice_rate="5187", discount_pct="2",
            gst_rate="18", tax_inclusive=True,
        )
        totals = calculate_purchase_invoice([battery, inverter])

        self.assertEqual(battery.basic_rate, Decimal("14727.97"))
        self.assertEqual(battery.taxable_amount, Decimal("27983.14"))
        self.assertEqual(inverter.basic_rate, Decimal("4395.76"))
        self.assertEqual(inverter.taxable_amount, Decimal("8615.69"))
        self.assertEqual(totals.taxable_amount, Decimal("36598.83"))
        self.assertEqual(totals.cgst_amount, Decimal("3293.89"))
        self.assertEqual(totals.sgst_amount, Decimal("3293.89"))
        self.assertEqual(totals.total_gst, Decimal("6587.78"))
        self.assertEqual(totals.round_off, Decimal("0.39"))
        self.assertEqual(totals.grand_total, Decimal("43187.00"))

    def test_interstate_invoice_uses_igst_only(self):
        line = calculate_purchase_line(
            qty=1, invoice_rate="1180", gst_rate="18",
            tax_inclusive=True, interstate=True,
        )
        self.assertEqual(line.basic_rate, Decimal("1000.00"))
        self.assertEqual(line.cgst_amount, Decimal("0.00"))
        self.assertEqual(line.sgst_amount, Decimal("0.00"))
        self.assertEqual(line.igst_amount, Decimal("180.00"))

    def test_exclusive_rate_and_discount(self):
        line = calculate_purchase_line(
            qty=3, invoice_rate="1000", discount_pct="10",
            gst_rate="12", tax_inclusive=False,
        )
        self.assertEqual(line.gross_taxable, Decimal("3000.00"))
        self.assertEqual(line.discount_amount, Decimal("300.00"))
        self.assertEqual(line.taxable_amount, Decimal("2700.00"))
        self.assertEqual(line.gst_amount, Decimal("324.00"))

    def test_invalid_discount_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_purchase_line(qty=1, invoice_rate=100, discount_pct=101)


if __name__ == "__main__":
    unittest.main()
