from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalogue.models import Category, Product, ProductVariant


class StaffCategoryAPITests(APITestCase):
    def setUp(self):
        self.list_url = reverse("staff-category-list")
        self.staff = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.customer = User.objects.create_user(
            phone="0709876543", password="strongpass123", first_name="Grace", last_name="Hopper"
        )

    def test_anonymous_request_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_staff_request_returns_403(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_cannot_view_staff_api_root(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get("/api/staff/catalogue/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_create_category(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(self.list_url, {"name": "Phones"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["slug"], "phones")

    def test_staff_can_update_category(self):
        self.client.force_authenticate(user=self.staff)
        category = Category.objects.create(name="Phones")
        detail_url = reverse("staff-category-detail", args=[category.pk])
        response = self.client.patch(detail_url, {"name": "Smartphones"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category.refresh_from_db()
        self.assertEqual(category.name, "Smartphones")

    def test_staff_can_delete_category(self):
        self.client.force_authenticate(user=self.staff)
        category = Category.objects.create(name="Phones")
        detail_url = reverse("staff-category-detail", args=[category.pk])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())


class StaffProductAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.client.force_authenticate(user=self.staff)
        self.category = Category.objects.create(name="Phones")
        self.list_url = reverse("staff-product-list")

    def test_create_product_with_variant_returns_201(self):
        payload = {
            "title": "Spark 10",
            "category": self.category.id,
            "brand": "Tecno",
            "variants": [
                {
                    "sku": "SPARK10-128",
                    "price": "450000.00",
                    "stock_qty": 10,
                    "attributes": {"storage": "128GB"},
                }
            ],
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(product.variants.count(), 1)
        self.assertEqual(product.variants.first().sku, "SPARK10-128")

    def test_create_product_without_variants_returns_400(self):
        payload = {
            "title": "Spark 10", "category": self.category.id, "brand": "Tecno", "variants": [],
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_product_ignores_variants_payload(self):
        product = Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        ProductVariant.objects.create(product=product, sku="SPARK10-128", price="450000.00")
        detail_url = reverse("staff-product-detail", args=[product.pk])
        response = self.client.patch(
            detail_url, {"title": "Spark 10 Pro", "variants": []}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertEqual(product.title, "Spark 10 Pro")
        self.assertEqual(product.variants.count(), 1)

    def test_non_staff_cannot_create_product(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.list_url, {"title": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_product_with_duplicate_variant_skus_does_not_partially_commit(self):
        payload = {
            "title": "Duplicate SKU Phone",
            "category": self.category.id,
            "brand": "Tecno",
            "variants": [
                {"sku": "DUPE-1", "price": "100000.00", "stock_qty": 5},
                {"sku": "DUPE-1", "price": "120000.00", "stock_qty": 3},
            ],
        }
        with self.assertRaises(IntegrityError):
            self.client.post(self.list_url, payload, format="json")
        self.assertFalse(
            Product.objects.filter(title="Duplicate SKU Phone").exists()
        )

    def test_update_with_nonempty_variants_returns_400(self):
        product = Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        ProductVariant.objects.create(product=product, sku="SPARK10-128", price="450000.00")
        detail_url = reverse("staff-product-detail", args=[product.pk])
        response = self.client.patch(
            detail_url,
            {"variants": [{"sku": "NEW-1", "price": "999.00", "stock_qty": 5}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        product.refresh_from_db()
        self.assertEqual(product.variants.count(), 1)
        self.assertEqual(product.variants.first().sku, "SPARK10-128")


class StaffProductVariantAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.client.force_authenticate(user=self.staff)
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.other_product = Product.objects.create(
            title="ThinkPad", category=self.category, brand="Lenovo"
        )
        self.list_url = reverse("staff-variant-list")

    def test_create_variant_for_product(self):
        response = self.client.post(
            f"{self.list_url}?product={self.product.id}",
            {
                "sku": "SPARK10-128", "price": "450000.00", "stock_qty": 10,
                "attributes": {"storage": "128GB"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product.variants.count(), 1)

    def test_create_with_non_numeric_product_param_returns_404_not_500(self):
        response = self.client.post(
            f"{self.list_url}?product=notanumber",
            {
                "sku": "SPARK10-128", "price": "450000.00", "stock_qty": 10,
                "attributes": {"storage": "128GB"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_with_non_numeric_product_param_returns_empty(self):
        response = self.client.get(f"{self.list_url}?product=notanumber")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_list_scoped_to_product(self):
        ProductVariant.objects.create(product=self.product, sku="A", price="100.00")
        ProductVariant.objects.create(product=self.other_product, sku="B", price="200.00")
        response = self.client.get(f"{self.list_url}?product={self.product.id}")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["sku"], "A")

    def test_patch_updates_stock_qty(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="A", price="100.00", stock_qty=5
        )
        detail_url = reverse("staff-variant-detail", args=[variant.pk])
        response = self.client.patch(detail_url, {"stock_qty": 50}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        variant.refresh_from_db()
        self.assertEqual(variant.stock_qty, 50)

    def test_non_staff_blocked(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
