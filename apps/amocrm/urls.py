from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

urlpatterns = [
    path("amotest/", csrf_exempt(views.test), name="amotest"),
]
