from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


@login_required
def index(request):
    return render(request, "storefront/account/index.html", {"active": "account"})


@login_required
def orders(request):  # Task 2
    return HttpResponse("orders (stub)")


@login_required
def order_detail(request, order_number):  # Task 2
    return HttpResponse("order detail (stub)")


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
