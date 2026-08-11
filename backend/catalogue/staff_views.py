from rest_framework import permissions, viewsets

from .models import Category, Product
from .staff_serializers import StaffCategorySerializer, StaffProductSerializer


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
