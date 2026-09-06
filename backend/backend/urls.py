from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("catalogue.urls")),
    path("api/staff/catalogue/", include("catalogue.staff_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("", include("storefront.urls")),
]

# Serve uploaded media from the app process. Render's free tier has no
# separate media host and USE_S3 is off, so this must run in production too.
# Acceptable at this project's scale (small, re-seeded demo catalogue); move
# to S3/R2 via USE_S3 when that changes. document_root is read per-request so
# test overrides of MEDIA_ROOT take effect.
def _serve_media(request, path):
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", _serve_media),
]
