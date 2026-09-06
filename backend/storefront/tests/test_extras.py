from decimal import Decimal

from django.test import SimpleTestCase

from storefront.templatetags.storefront_extras import ugx, variant_label


class UgxFilterTests(SimpleTestCase):
    def test_formats_integer_with_thousands_and_prefix(self):
        self.assertEqual(ugx(2800000), "UGX 2,800,000")

    def test_formats_decimal_without_cents(self):
        self.assertEqual(ugx(Decimal("1950000.00")), "UGX 1,950,000")

    def test_handles_none(self):
        self.assertEqual(ugx(None), "—")


class VariantLabelTests(SimpleTestCase):
    def test_joins_attribute_values(self):
        self.assertEqual(variant_label({"storage": "128GB", "color": "Black"}), "128GB / Black")

    def test_empty_attributes_returns_standard(self):
        self.assertEqual(variant_label({}), "Standard")

    def test_non_dict_returns_standard(self):
        self.assertEqual(variant_label(None), "Standard")
