from django.urls import include, path
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from .staff_views import StaffCategoryViewSet

router = DefaultRouter()
router.register("categories", StaffCategoryViewSet, basename="staff-category")
router.APIRootView.permission_classes = [permissions.IsAdminUser]

urlpatterns = [
    path("", include(router.urls)),
]
