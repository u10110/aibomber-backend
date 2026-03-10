# -*- encoding: utf-8 -*-
from django.apps import AppConfig


class MyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users_control'
    label = 'apps_users_control'
