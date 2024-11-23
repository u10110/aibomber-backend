# -*- encoding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path("advertising/", login_required(views.advertising), name="advertising"),
    path("actual-bids/", login_required(views.actual_bids), name="actual-bids"),
]

# name - имя для path(), к нему можно обратиться из кода,
# чтобы установить ссылку на страницу сайта.
