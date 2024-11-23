# -*- encoding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt

from apps.seo import views

urlpatterns = [
    path("product-card/", login_required(views.product_card), name="product-card"),
    path(
        "seo-group-result/",
        login_required(views.seo_group_result),
        name="seo-group-result",
    ),
    path(
        "seo-group-search/",
        login_required(views.seo_group_search),
        name="seo-group-search",
    ),
    path(
        "product-card-search/",
        login_required(views.product_card_search),
        name="product-card-search",
    ),
    path(
        "selection-requests/",
        login_required(views.selection_requests),
        name="selection-requests",
    ),
    path("frequency/", csrf_exempt(views.frequency), name="frequency"),
]
