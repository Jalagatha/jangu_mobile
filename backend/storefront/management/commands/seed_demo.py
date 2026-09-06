"""Populate a demo Jangu catalogue. Idempotent; safe to run on every deploy."""

import io
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from catalogue.models import Category, Product, ProductImage, ProductVariant

CATEGORIES = [
    "Smartphones", "Laptops & Accessories", "Audio & Wearables", "Gaming Gear",
]

# title, category, brand, [ (sku_suffix, attributes, price, stock) ]
PRODUCTS = [
    ("Samsung Galaxy S23", "Smartphones", "Samsung", [
        ("128", {"storage": "128GB", "color": "Black"}, "2800000", 20),
        ("256", {"storage": "256GB", "color": "Cream"}, "3050000", 12)]),
    ("Infinix Note 50 Pro", "Smartphones", "Infinix", [
        ("256", {"storage": "256GB", "color": "Titan Grey"}, "1950000", 30)]),
    ("iPhone 15 Pro", "Smartphones", "Apple", [
        ("128", {"storage": "128GB", "color": "Natural Titanium"}, "5200000", 15),
        ("256", {"storage": "256GB", "color": "Blue Titanium"}, "5750000", 9)]),
    ("Tecno Camon 30", "Smartphones", "Tecno", [
        ("256", {"storage": "256GB", "color": "Black"}, "1350000", 25)]),
    ("MacBook Air M3", "Laptops & Accessories", "Apple", [
        ("8-256", {"ram": "8GB", "storage": "256GB"}, "6900000", 8)]),
    ("Dell XPS 13", "Laptops & Accessories", "Dell", [
        ("16-512", {"ram": "16GB", "storage": "512GB"}, "7400000", 6)]),
    ("HP Pavilion 15", "Laptops & Accessories", "HP", [
        ("16-512", {"ram": "16GB", "storage": "512GB"}, "3600000", 14)]),
    ("Anker 65W GaN Charger", "Laptops & Accessories", "Anker", [
        ("std", {}, "180000", 60)]),
    ("Sony WH-1000XM5", "Audio & Wearables", "Sony", [
        ("blk", {"color": "Black"}, "1250000", 18)]),
    ("JBL Tune 770NC", "Audio & Wearables", "JBL", [
        ("blk", {"color": "Black"}, "420000", 40)]),
    ("Apple AirPods Pro 2", "Audio & Wearables", "Apple", [
        ("usbc", {"connectivity": "USB-C"}, "950000", 22)]),
    ("Apple Watch Series 9", "Audio & Wearables", "Apple", [
        ("41", {"size": "41mm", "connectivity": "GPS"}, "1600000", 10)]),
    ("Samsung Galaxy Watch 6", "Audio & Wearables", "Samsung", [
        ("40", {"size": "40mm"}, "1150000", 13)]),
    ("Sony PlayStation 5 DualSense", "Gaming Gear", "Sony", [
        ("wht", {"color": "White"}, "380000", 35)]),
    ("Xbox Wireless Controller", "Gaming Gear", "Microsoft", [
        ("blk", {"color": "Carbon Black"}, "320000", 28)]),
    ("Logitech G502 HERO Mouse", "Gaming Gear", "Logitech", [
        ("blk", {"color": "Black"}, "190000", 45)]),
]


def _slug_of(title):
    from django.utils.text import slugify
    return slugify(title)


def _placeholder_png(label):
    img = Image.new("RGB", (600, 600), "#12356E")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 500, 600, 600], fill="#EF7C1B")
    d.rectangle([60, 60, 540, 460], outline="#ffffff", width=6)
    d.text((60, 250), label[:22], fill="#ffffff")
    d.text((70, 525), "JANGU MOBILE", fill="#12356E")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class Command(BaseCommand):
    help = "Populate a demo catalogue (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true",
                            help="Delete demo rows first (dev only).")

    def handle(self, *args, **opts):
        if opts["flush"]:
            demo_slugs = [_slug_of(title) for title, *_ in PRODUCTS]
            ProductImage.objects.filter(product__slug__in=demo_slugs).delete()
            ProductVariant.objects.filter(product__slug__in=demo_slugs).delete()
            Product.objects.filter(slug__in=demo_slugs).delete()
            Category.objects.filter(slug__in=[_slug_of(n) for n in CATEGORIES]).delete()

        created_c = created_p = 0
        cats = {}
        for name in CATEGORIES:
            cat, made = Category.objects.get_or_create(slug=_slug_of(name), defaults={"name": name})
            cats[name] = cat
            created_c += made

        for title, cat_name, brand, variants in PRODUCTS:
            product, made = Product.objects.get_or_create(
                slug=_slug_of(title),
                defaults={"title": title, "brand": brand, "category": cats[cat_name],
                          "description": f"{brand} {title} — genuine, warrantied, delivered fast."},
            )
            created_p += made
            for suffix, attrs, price, stock in variants:
                ProductVariant.objects.get_or_create(
                    sku=f"{_slug_of(title)}-{suffix}",
                    defaults={"product": product, "attributes": attrs,
                              "price": Decimal(price), "stock_qty": stock},
                )
            if not product.images.exists():
                pi = ProductImage(product=product)
                pi.image.save(f"{_slug_of(title)}.png",
                              ContentFile(_placeholder_png(title)), save=True)

        self.stdout.write(self.style.SUCCESS(
            f"seed_demo: categories +{created_c}/{len(CATEGORIES)}, "
            f"products +{created_p}/{len(PRODUCTS)}."))
