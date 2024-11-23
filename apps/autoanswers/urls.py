from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path(
        "create-autoanswers/",
        login_required(views.create_autoanswers),
        name="create-autoanswers",
    ),
]
