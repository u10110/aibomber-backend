# -*- encoding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from django.urls import path, re_path

from . import views
from .views import *
from apps.home.api import auth_login


from django.urls import path
# from .views import telegram_login_view
from .views import LoginCallbackView




urlpatterns = [
    path("api/login/", auth_login, name="auth_login"),
    path("login/", login_view, name="login"),


    re_path(r"^signup/?$", register_user, name="register"),
    path("api/v1/signup_tg/", register_tg_user, name="register_tg"),
    path("api/v1/reset_tg_password/", reset_tg_password, name="reset_tg_password"),
    # re_path(r'^register-dev123$', register_user, name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    re_path(r"^activate/(?P<code>[0-9]+)/$", activate, name="activate"),
    # re_path(r'^phone/(?P<phone>[0-9]+)/$', check_phone, name='check_phone'),
    re_path(r"^legal/?$", legal, name="legal"),
    re_path(r"^privacy/?$", privacy, name="privacy"),
    re_path(r"^policy/?$", policy, name="policy"),
    re_path(r"^send-sms-again$", send_sms_again, name="send-sms-again"),
    re_path(r"^send-sms-reset$", send_sms_reset, name="send-sms-reset"),
    re_path(
        r"^reset_password/(?P<code>[0-9]+)/$", reset_password, name="reset_password"
    ),
    path("reset_password_done/", reset_password_done, name="reset_password_done"),
    
    # path('telegram-login/', telegram_login_view, name='telegram_login'),
    path('telegram/callback/', LoginCallbackView.as_view(), name='telegram_callback'),

    
    # path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', views.activate, name='activate'),
    # re_path(r'^activate/?P<uidb64>?P<token>/$', views.activate, name='activate')
]
