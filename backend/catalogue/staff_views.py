from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets

from .models import Category, Product, ProductVariant
from .staff_serializers import (
    StaffCategorySerializer,
    StaffProductSerializer,
    StaffProductVariantSerializer,
)


class StaffCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffCategorySerializer
    queryset = Category.objects.all()
    pagination_class = None


class StaffProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffProductSerializer
    queryset = Product.objects.all()
    pagination_class = None


class StaffProductVariantViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffProductVariantSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = ProductVariant.objects.all()
        product_id = self.request.query_params.get("product")
        if product_id is not None:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.request.query_params.get("product"))
        serializer.save(product=product)
