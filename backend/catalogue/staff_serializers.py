from rest_framework import serializers

from .models import Category


class StaffCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "image"]
        read_only_fields = ["slug"]
