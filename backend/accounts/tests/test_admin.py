from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User


class UserAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_superuser(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.customer = User.objects.create_user(
            phone="0709876543",
            password="strongpass123",
            first_name="Grace",
            last_name="Hopper",
        )

    def test_staff_can_access_user_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_redirected_from_admin(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_render_add_user_form(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:accounts_user_add"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_create_user_via_admin(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "phone": "0700111222",
                "first_name": "New",
                "last_name": "Staffer",
                "password1": "SuperSecret123!",
                "password2": "SuperSecret123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(phone="+256700111222")
        self.assertTrue(created.check_password("SuperSecret123!"))

    def test_staff_can_render_change_user_form(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(
            reverse("admin:accounts_user_change", args=[self.customer.pk])
        )
        self.assertEqual(response.status_code, 200)
