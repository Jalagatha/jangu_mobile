from django.http import HttpResponse
from django.shortcuts import render

from catalogue.models import Category
from storefront import selectors


def home(request):
    categories = Category.objects.filter(parent__isnull=True).order_by("name")
    return render(request, "storefront/home.html", {
        "categories": categories,
        "first_category": categories.first(),
        "featured": selectors.featured_products(8),
        "active": "home",
    })


def category(request, slug):  # replaced in Task 7
    return HttpResponse("category (stub)")


def search(request):  # replaced in Task 7
    return HttpResponse("search (stub)")


def product_detail(request, slug):  # replaced in Task 8
    return HttpResponse("product (stub)")
