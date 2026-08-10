from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .staff_views import StaffCategoryViewSet

router = DefaultRouter()
router.register("categories", StaffCategoryViewSet, basename="staff-category")

urlpatterns = [
    path("", include(router.urls)),
]
