from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccountIndexTests(TestCase):
    def test_requires_login(self):
        r = self.client.get(reverse("storefront:account"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])

    def test_renders_greeting_and_tiles(self):
        user = User.objects.create_user(
            phone="+256772000001", password="s3cure-pass-99", first_name="Ada", last_name="L"
        )
        self.client.force_login(user)
        r = self.client.get(reverse("storefront:account"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Hi Ada")
        self.assertContains(r, reverse("storefront:account_orders"))
        self.assertContains(r, reverse("storefront:addresses"))
        self.assertContains(r, reverse("storefront:logout"))
