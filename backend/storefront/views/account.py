from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from orders.models import Order


@login_required
def index(request):
    return render(request, "storefront/account/index.html", {"active": "account"})


@login_required
def orders(request):
    page = Paginator(request.user.orders.all(), 10).get_page(request.GET.get("page"))
    return render(request, "storefront/account/orders.html", {"page_obj": page, "active": "account"})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "storefront/account/order_detail.html", {"order": order, "active": "account"})


@login_required
def order_cancel(request, order_number):  # Task 3
    return HttpResponse("order cancel (stub)")


@login_required
def addresses(request):  # Task 4
    return HttpResponse("addresses (stub)")


@login_required
def address_add(request):  # Task 4
    return HttpResponse("address add (stub)")


@login_required
def address_edit(request, pk):  # Task 4
    return HttpResponse("address edit (stub)")


@login_required
def address_delete(request, pk):  # Task 4
    return HttpResponse("address delete (stub)")


@login_required
def address_set_default(request, pk):  # Task 4
    return HttpResponse("address set default (stub)")
