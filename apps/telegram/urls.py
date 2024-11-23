from django.urls import re_path, path, include
from rest_framework import routers
from rest_framework.authtoken import views as token_views

from apps.telegram import views
from apps.telegram.auth.views import TgLoginApi, TgLogoutApi, create_magic_link_login, execute_magic_link
from apps.telegram.views import UserAlertsView

router = routers.DefaultRouter()
router.register(r"user_alerts", UserAlertsView, basename="user-alerts")

urlpatterns = [
    path("", include(router.urls)),
    re_path(r"get_statistic", views.GetStatisticView.as_view(), name="get-statistic"),
    re_path(r"turn_on_notifications", views.SendNotificationsView.as_view(), name="turn-on-notifications"),
    re_path(r"save_tg_message_into_db", views.SaveTgMessagesView.as_view(), name="save-tg-message-into-db"),
    re_path(r"tg_login", TgLoginApi.as_view(), name="tg-login"),
    re_path(r"tg_logout", TgLogoutApi.as_view(), name="tg-logout"),
    path('create_magic_link/', create_magic_link_login, name="create-magic-link"),
    path('magic_link/', execute_magic_link, name="magic-link"),
    re_path(r"api-token-auth", token_views.obtain_auth_token)
]
