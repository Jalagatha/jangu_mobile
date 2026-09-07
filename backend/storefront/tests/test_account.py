from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import Order, OrderItem
from orders.tests.factories import make_user, make_variant

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


class OrderHistoryTests(TestCase):
    def setUp(self):
        self.user = make_user(phone="+256772000001")
        self.other = make_user(phone="+256772000002")
        self.client.force_login(self.user)

    def _order(self, owner, number, status=Order.Status.PAID):
        order = Order.objects.create(
            user=owner, order_number=number, status=status,
            subtotal=Decimal("1000000"), total=Decimal("1000000"),
            recipient_name="Ada", recipient_phone="+256772000009",
            city_district="Kampala", street_area="Kololo",
        )
        OrderItem.objects.create(
            order=order, variant=make_variant(sku=number), product_title="Phone X",
            variant_label="128GB", quantity=1, unit_price=Decimal("1000000"),
        )
        return order

    def test_history_lists_only_own_orders(self):
        self._order(self.user, "JNG-20260906-0001")
        self._order(self.other, "JNG-20260906-0002")
        r = self.client.get(reverse("storefront:account_orders"))
        self.assertContains(r, "JNG-20260906-0001")
        self.assertNotContains(r, "JNG-20260906-0002")

    def test_history_requires_login(self):
        self.client.logout()
        r = self.client.get(reverse("storefront:account_orders"))
        self.assertIn("/login/", r["Location"])

    def test_detail_shows_items_and_total(self):
        order = self._order(self.user, "JNG-20260906-0003")
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Phone X")
        self.assertContains(r, "UGX 1,000,000")

    def test_detail_404_for_another_users_order(self):
        order = self._order(self.other, "JNG-20260906-0004")
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertEqual(r.status_code, 404)
