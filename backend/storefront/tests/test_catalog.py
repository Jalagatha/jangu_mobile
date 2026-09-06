import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from storefront.tests.factories import make_category, make_product


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CategoryPageTests(TestCase):
    def setUp(self):
        self.phones = make_category("Smartphones")
        make_product(title="Galaxy S23", category=self.phones, brand="Samsung", price="2800000", stock_qty=5)
        make_product(title="Note 50 Pro", category=self.phones, brand="Infinix", price="1950000", stock_qty=0)
        make_product(title="MacBook", category=make_category("Laptops"), brand="Apple", price="6900000")

    def test_lists_only_category_products(self):
        r = self.client.get(reverse("storefront:category", args=[self.phones.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Galaxy S23")
        self.assertContains(r, "Note 50 Pro")
        self.assertNotContains(r, "MacBook")

    def test_brand_filter(self):
        r = self.client.get(reverse("storefront:category", args=[self.phones.slug]), {"brand": "Samsung"})
        self.assertContains(r, "Galaxy S23")
        self.assertNotContains(r, "Note 50 Pro")

    def test_price_sort_asc(self):
        r = self.client.get(reverse("storefront:category", args=[self.phones.slug]), {"sort": "price_asc"})
        self.assertLess(r.content.index(b"Note 50 Pro"), r.content.index(b"Galaxy S23"))

    def test_in_stock_filter(self):
        r = self.client.get(reverse("storefront:category", args=[self.phones.slug]), {"in_stock": "1"})
        self.assertContains(r, "Galaxy S23")
        self.assertNotContains(r, "Note 50 Pro")

    def test_unknown_category_404(self):
        self.assertEqual(self.client.get(reverse("storefront:category", args=["nope"])).status_code, 404)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SearchPageTests(TestCase):
    def setUp(self):
        self.phones = make_category("Smartphones")
        make_product(title="Galaxy S23", category=self.phones, brand="Samsung", price="2800000")
        make_product(title="AirPods Pro", category=self.phones, brand="Apple", price="950000",
                     stock_qty=3)

    def test_search_matches_brand(self):
        r = self.client.get(reverse("storefront:search"), {"q": "apple"})
        self.assertContains(r, "AirPods Pro")
        self.assertNotContains(r, "Galaxy S23")

    def test_empty_query_lists_all_active(self):
        r = self.client.get(reverse("storefront:search"), {"q": ""})
        self.assertContains(r, "Galaxy S23")
        self.assertContains(r, "AirPods Pro")
