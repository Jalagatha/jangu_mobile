from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalogue.models import Category


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
