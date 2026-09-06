import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings

from catalogue.models import Category, Product, ProductImage, ProductVariant


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SeedDemoTests(TestCase):
    def test_creates_catalogue(self):
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Category.objects.count(), 4)
        self.assertGreaterEqual(Product.objects.count(), 12)
        self.assertTrue(all(p.variants.exists() for p in Product.objects.all()))
        self.assertTrue(all(p.images.exists() for p in Product.objects.all()))
        self.assertTrue(all(v.price > 0 for v in ProductVariant.objects.all()))

    def test_is_idempotent(self):
        call_command("seed_demo", verbosity=0)
        c1, p1, v1, i1 = (Category.objects.count(), Product.objects.count(),
                          ProductVariant.objects.count(), ProductImage.objects.count())
        call_command("seed_demo", verbosity=0)
        self.assertEqual(
            (c1, p1, v1, i1),
            (Category.objects.count(), Product.objects.count(),
             ProductVariant.objects.count(), ProductImage.objects.count()),
        )
