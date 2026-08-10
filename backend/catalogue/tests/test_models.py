import tempfile

from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings

from catalogue.models import Category, Product, ProductImage, ProductVariant
from catalogue.tests.helpers import make_test_image


class CategoryModelTests(TestCase):
    def test_slug_auto_generated_from_name(self):
        category = Category.objects.create(name="Mobile Phones")
        self.assertEqual(category.slug, "mobile-phones")

    def test_slug_collision_appends_suffix(self):
        Category.objects.create(name="Phones")
        second = Category.objects.create(name="Phones")
        self.assertEqual(second.slug, "phones-2")

    def test_explicit_slug_is_preserved(self):
        category = Category.objects.create(name="Tablets", slug="custom-slug")
        self.assertEqual(category.slug, "custom-slug")

    def test_nested_parent_child_relationship(self):
        electronics = Category.objects.create(name="Electronics")
        phones = Category.objects.create(name="Phones", parent=electronics)
        smartphones = Category.objects.create(name="Smartphones", parent=phones)
        self.assertEqual(smartphones.parent, phones)
        self.assertEqual(smartphones.parent.parent, electronics)

    def test_children_related_name(self):
        electronics = Category.objects.create(name="Electronics")
        phones = Category.objects.create(name="Phones", parent=electronics)
        self.assertIn(phones, electronics.children.all())


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")

    def test_slug_auto_generated_from_title(self):
        product = Product.objects.create(
            title="Tecno Spark 10", category=self.category, brand="Tecno"
        )
        self.assertEqual(product.slug, "tecno-spark-10")

    def test_slug_collision_appends_suffix(self):
        Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        second = Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        self.assertEqual(second.slug, "spark-10-2")

    def test_is_active_defaults_to_true(self):
        product = Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        self.assertTrue(product.is_active)

    def test_category_protected_on_delete(self):
        Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        with self.assertRaises(ProtectedError):
            self.category.delete()


class ProductVariantModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )

    def test_attributes_default_to_empty_dict(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        self.assertEqual(variant.attributes, {})

    def test_attributes_json_roundtrip(self):
        variant = ProductVariant.objects.create(
            product=self.product,
            sku="SPARK10-128-BLK",
            price="450000.00",
            attributes={"storage": "128GB", "color": "Black"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.attributes, {"storage": "128GB", "color": "Black"})

    def test_stock_qty_defaults_to_zero(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        self.assertEqual(variant.stock_qty, 0)

    def test_in_stock_property(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00", stock_qty=5
        )
        self.assertTrue(variant.in_stock)
        variant.stock_qty = 0
        self.assertFalse(variant.in_stock)

    def test_sku_unique(self):
        ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        with self.assertRaises(IntegrityError):
            ProductVariant.objects.create(
                product=self.product, sku="SPARK10-128-BLK", price="450000.00"
            )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProductImageModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )

    def test_first_image_is_auto_primary(self):
        image = ProductImage.objects.create(product=self.product, image=make_test_image())
        self.assertTrue(image.is_primary)

    def test_new_primary_unsets_previous_primary(self):
        first = ProductImage.objects.create(
            product=self.product, image=make_test_image("a.png")
        )
        second = ProductImage.objects.create(
            product=self.product, image=make_test_image("b.png"), is_primary=True
        )
        first.refresh_from_db()
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_sort_order_defaults_to_zero(self):
        image = ProductImage.objects.create(product=self.product, image=make_test_image())
        self.assertEqual(image.sort_order, 0)
