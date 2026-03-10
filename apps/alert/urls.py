# -*- encoding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt

from apps.alert import views

urlpatterns = [
    # (r'^admin/', include(admin.site.urls)),
    path(
        "alert/<status>/", csrf_exempt(views.handle), name="handle"
    ),  # success, failure, start http://127.0.0.1:8000/api/alert/failure/
    path("alert-user/<status>/", csrf_exempt(views.handle_user), name="handle_user"),
    path("get-sms/", csrf_exempt(views.handle_user_sms), name="handle_user_sms"),
    # path("sbp-page/", csrf_exempt(views.sbp_page), name="sbp_pay"),
    path("billing_check/", csrf_exempt(views.billing_check), name="billing_check"),
    path(
        "read-notifications/",
        csrf_exempt(views.read_notifications),
        name="read-notifications",
    ),
    path("refresh-tg", csrf_exempt(views.refresh_tg_amo)),
    path("refresh-website", csrf_exempt(views.refresh_website_amo)),
    path("check-amo-tokens", csrf_exempt(views.check_amo_tokens)),
]
