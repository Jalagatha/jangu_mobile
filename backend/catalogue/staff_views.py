from rest_framework import permissions, viewsets

from .models import Category
from .staff_serializers import StaffCategorySerializer


class StaffCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffCategorySerializer
    queryset = Category.objects.all()
    pagination_class = None
