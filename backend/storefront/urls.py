from django.urls import path

from storefront.views import auth, cart, catalog, checkout

app_name = "storefront"

urlpatterns = [
    path("", catalog.home, name="home"),
    path("c/<slug:slug>/", catalog.category, name="category"),
    path("search/", catalog.search, name="search"),
    path("p/<slug:slug>/", catalog.product_detail, name="product"),
    path("cart/", cart.detail, name="cart"),
    path("cart/add/", cart.add, name="cart_add"),
    path("cart/update/", cart.update, name="cart_update"),
    path("cart/remove/", cart.remove, name="cart_remove"),
    path("register/", auth.register, name="register"),
    path("login/", auth.StorefrontLoginView.as_view(), name="login"),
    path("logout/", auth.logout_view, name="logout"),
    path("checkout/", checkout.checkout, name="checkout"),
    path("checkout/payment/", checkout.payment, name="payment"),
    path("orders/<str:order_number>/", checkout.order_confirmation, name="order_confirmation"),
]
