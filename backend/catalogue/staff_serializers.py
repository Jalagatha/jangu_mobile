from rest_framework import serializers

from .models import Category, Product, ProductVariant


class StaffCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "image"]
        read_only_fields = ["slug"]


class StaffProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "attributes", "price", "stock_qty"]
        read_only_fields = ["id"]


class StaffProductSerializer(serializers.ModelSerializer):
    variants = StaffProductVariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title", "category", "description", "brand",
            "is_active", "variants",
        ]
        read_only_fields = ["slug"]

    def create(self, validated_data):
        variants_data = validated_data.pop("variants", [])
        if not variants_data:
            raise serializers.ValidationError(
                {"variants": "A product needs at least one variant."}
            )
        product = Product.objects.create(**validated_data)
        for variant_data in variants_data:
            ProductVariant.objects.create(product=product, **variant_data)
        return product

    def update(self, instance, validated_data):
        validated_data.pop("variants", None)
        return super().update(instance, validated_data)
