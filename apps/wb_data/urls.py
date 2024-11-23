# -*- encoding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path

from apps.billing import views as b_views
from apps.home import views

urlpatterns = [
    path("api-tokens/", login_required(views.api_tokens), name="api-tokens"),
    path(
        "api-tokens/<int:pk>/delete/",
        login_required(views.api_delete),
        name="api-delete",
    ),
    path("api-tokens/<int:pk>/edit/", login_required(views.api_edit), name="api-edit"),
    path(
        "add-api-tokens/",
        login_required(views.add_suppliers_api),
        name="add-api-tokens",
    ),
    path(
        "products/",
        login_required(views.products),
        name="products",
    ),
]
