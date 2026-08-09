from django.test import TestCase

from catalogue.models import Category


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
