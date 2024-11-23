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
    path("sbp_pay/", csrf_exempt(views.sbp_pay), name="sbp_pay"),
    # path("sbp-page/", csrf_exempt(views.sbp_page), name="sbp_pay"),
    re_path(r"^sbp-page/?$", csrf_exempt(views.sbp_page), name="sbp_pay"),
    path("wb-buy/", csrf_exempt(views.wb_buy), name="wb_buy"),
    path("billing_check/", csrf_exempt(views.billing_check), name="billing_check"),
    path("review-add/", csrf_exempt(views.review_add), name="review_add"),
    path("favorite-add/", csrf_exempt(views.favorite_add), name="favorite_add"),
    path("question-add/", csrf_exempt(views.question_add), name="question_add"),
    path(
        "favorite-review-add/",
        csrf_exempt(views.favorite_review_add),
        name="favorite_review_add",
    ),
    path("wb-pay-check/", csrf_exempt(views.wb_pay_check), name="wb_pay_check"),
    path("wb-check-code/", csrf_exempt(views.wb_check_code), name="wb_check_code"),
    path("eramp/", csrf_exempt(views.eramp), name="eramp"),
    path(
        "eramp/change-subscription/",
        csrf_exempt(views.eramp_change_subscription),
        name="eramp_change_subscription",
    ),
    path(
        "eramp/eramp-get-end-date/",
        csrf_exempt(views.eramp_get_end_date),
        name="eramp_get_end_date",
    ),
    path("positions/", csrf_exempt(views.position), name="position"),
    path("cpm/", csrf_exempt(views.advertising_rate), name="advertising_rate"),
    path("check-proxy/", csrf_exempt(views.check_proxy)),
    path("get-pvz/", csrf_exempt(views.get_pvz), name="get-pvz"),
    path(
        "read-notifications/",
        csrf_exempt(views.read_notifications),
        name="read-notifications",
    ),
    path("refresh-tg", csrf_exempt(views.refresh_tg_amo)),
    path("refresh-website", csrf_exempt(views.refresh_website_amo)),
    path("check-amo-tokens", csrf_exempt(views.check_amo_tokens)),
    path("test-buyout", csrf_exempt(views.wb_buy_test)),
    path("test-review", csrf_exempt(views.review_add_test)),
    path("test-favorite-add", csrf_exempt(views.favorite_add_test)),
    path("test-question-add", csrf_exempt(views.question_add_test)),
    path("test-favorite-review-add", csrf_exempt(views.favorite_review_add_test)),
]
