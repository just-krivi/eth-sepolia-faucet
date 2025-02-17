from django.contrib import admin
from django.urls import path, include, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from faucet.streamlit_view import StreamlitProxyView

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/",
        include(
            [
                path("schema", SpectacularAPIView.as_view(), name="schema"),
                path(
                    "schema/swagger-ui",
                    SpectacularSwaggerView.as_view(url_name="schema"),
                    name="swagger-ui",
                ),
                path("", include("faucet.urls")),  # Include faucet URLs under /api/
            ]
        ),
    ),
    # Catch all other URLs and send them to Streamlit
    re_path(r"^(?P<path>.*)$", StreamlitProxyView.as_view(), name="home"),
]
