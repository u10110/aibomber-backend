# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.conf import settings
from django.conf.urls import handler404, handler500
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path  # add this


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path("sentry-debug/", trigger_error),
    path("__debug__/", include("debug_toolbar.urls")),
    path("dev-admin8/", admin.site.urls),  # Django admin route
    # path("dashboard/", include("apps.home.urls")),             # UI Kits Html files
    path("api/", include("apps.alert.urls")),  # UI Kits Html files
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("apps.authentication.urls")),  # Auth routes - login / register
    path("", include("apps.home.urls")),  # UI Kits Html files
    path("", include("apps.telegram.urls")),
    path("", include("apps.amocrm.urls")),  # UI Kits Html files
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler500 = "apps.home.views.error_500"
handler404 = "apps.home.views.error_404"
