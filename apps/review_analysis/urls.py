# -*- encoding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path(
        "review-analysis/", login_required(views.review_tasks), name="review-analysis"
    ),
    path("review-analysis/<int:pk>", login_required(views.review_details)),
    path(
        "review-analysis-delete", login_required(views.delete_task), name="delete-task"
    ),
    path("review-analysis-check", login_required(views.check_task), name="check-task"),
    path("export-review", login_required(views.export_tasks)),
]
