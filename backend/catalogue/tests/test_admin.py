from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from catalogue.models import Category, Product


class CatalogueAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.customer = User.objects.create_user(
            phone="0709876543", password="strongpass123", first_name="Grace", last_name="Hopper"
        )
        Category.objects.create(name="Phones")

    def test_staff_can_access_category_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:catalogue_category_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_product_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:catalogue_product_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_redirected_from_category_changelist(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("admin:catalogue_category_changelist"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_render_product_change_form_with_inlines(self):
        category = Category.objects.get(name="Phones")
        product = Product.objects.create(title="iPhone 15", category=category, brand="Apple")
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:catalogue_product_change", args=[product.pk]))
        self.assertEqual(response.status_code, 200)
