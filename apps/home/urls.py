# -*- encoding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt

from apps.billing import views as b_views
from apps.home import views

urlpatterns = [
    # The home page
    # path("", views.error, name="error"),
    path("", login_required(views.index), name="home"),
    # (r'^accounts/', include('registration.urls'),
    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls),
    path("upload/", login_required(views.upload), name="upload"),
    path("pvz/", login_required(views.pvz), name="pvz"),
    path("pricing/", login_required(views.pricing), name="pricing"),
    path(
        "account-billing/",
        login_required(views.account_billing),
        name="account-billing",
    ),
    path(
        "buyout/<int:pk>/delete/",
        login_required(views.buyout_delete),
        name="buyout-delete",
    ),
    path(
        r"review/<int:pk>/delete$",
        login_required(views.review_delete),
        name="review-delete",
    ),
    path(
        "review/<int:pk>/delete/excluded/",
        login_required(views.review_delete_excluded),
        name="review-delete-excluded",
    ),
    re_path(r"^buyout$", login_required(views.buyout), name="buyout"),
    re_path(r"^reviews$", login_required(views.reviews), name="reviews"),
    re_path(r"^delivery$", login_required(views.delivery), name="delivery"),
    # path('delivery/', login_required(views.delivery), name='delivery'),
    path("buyout/create/", login_required(views.buyout_create), name="buyout_create"),
    path(
        "auto-pay-stop/<int:group>/",
        login_required(views.auto_pay_stop),
        name="auto-pay-stop",
    ),
    path("pvz/<int:pk>/delete/", login_required(views.pvz_delete), name="pvz-delete"),
    path(
        "pvz/all-delete/", login_required(views.pvz_all_delete), name="pvz-all-delete"
    ),
    path("reviews/<int:pk>/add/", login_required(views.add_review), name="add-review"),
    path(
        "add-to-favorite/",
        login_required(views.add_to_favorite),
        name="add-to-favorite",
    ),
    path(
        "add-to-favorite/<int:pk>/delete/",
        login_required(views.favorite_delete),
        name="favorite-delete",
    ),
    path("add-question/", login_required(views.add_question), name="add-question"),
    path("add-to-cart/", login_required(views.add_to_cart), name="add-to-cart"),
    path(
        "add-to-waiting/", login_required(views.add_to_waiting), name="add-to-waiting"
    ),
    path(
        "add-like-to-review/",
        login_required(views.add_like_to_review),
        name="add-like-to-review",
    ),
    path(
        "get_likes_data/", login_required(views.get_likes_data), name="get_likes_data"
    ),
    path("add-card/", login_required(views.add_card), name="add-card"),
    # path('app-download/', login_required(views.app_download), name='app-download'),
    path("add-sms-cloud/", login_required(views.add_sms_cloud), name="add-sms-cloud"),
    path("get-tochka-phone/", views.get_tochka_phone, name="get-tochka-phone"),
    path(
        "add-card/<int:pk>/delete/",
        login_required(views.card_delete),
        name="card-delete",
    ),
    path("account/", login_required(views.account), name="account"),
    re_path(
        r"^export_buyout$", login_required(views.export_buyout), name="export_buyout"
    ),
    re_path(
        r"^export_delivery$",
        login_required(views.export_delivery),
        name="export_delivery",
    ),
    re_path(
        r"^export_reviews$", login_required(views.export_reviews), name="export_reviews"
    ),
    path("create_order/", login_required(b_views.create_order), name="create_order"),
    re_path(r"^bill/?$", csrf_exempt(b_views.pay_buyout), name="bill"),
    re_path(r"^bill/success$", login_required(b_views.bill_ok), name="bill_ok"),
    re_path(r"^bill/error$", login_required(b_views.bill_bad), name="bill_bad"),
    path(
        "prolongation-tariff/",
        login_required(b_views.prolongation),
        name="prolongation-tariff",
    ),
    path(
        "prolongation-order/",
        login_required(b_views.prolongation_order),
        name="prolongation-order",
    ),
    path(
        "prolongation-pay/",
        login_required(b_views.prolongation_pay),
        name="prolongation-pay",
    ),
    path(
        "prolongation-pay-link/",
        login_required(b_views.prolongation_pay_link),
        name="prolongation-pay-link",
    ),
    path(
        "check-promocode/",
        login_required(b_views.check_promocode),
        name="check_promocode",
    ),
    path(
        "create-promocode/",
        csrf_exempt(b_views.create_promocode),
        name="create_promocode",
    ),
    path("get_size/", login_required(views.get_size), name="get_size"),
    re_path(r"^questions/?$", login_required(views.questions), name="questions"),
    path(
        "question/create/",
        login_required(views.question_create),
        name="question-create",
    ),
    path(
        r"question/<int:pk>/delete$",
        login_required(views.question_delete),
        name="question-delete",
    ),
    path("faq/", views.faq, name="faq"),
    path("lessons/", views.lessons, name="lessons"),
    path(
        "search-promotion/",
        login_required(views.search_promotion),
        name="search-promotion",
    ),
    path(
        "search-promotion/<int:pk>/stop/",
        login_required(views.search_promotion_stop),
        name="search-promotion-stop",
    ),
    path(
        "search-promotion/<int:pk>/start/",
        login_required(views.search_promotion_start),
        name="search-promotion-start",
    ),
    path("positions/", login_required(views.positions), name="positions"),
    path(
        "position/<int:pk>/details/",
        login_required(views.position_details),
        name="position-details",
    ),
    path(
        "position/<int:pk>/delete/",
        login_required(views.position_delete),
        name="position-delete",
    ),
    path("dbs/", login_required(views.dbs), name="dbs"),
    path(
        "show-more-review/",
        login_required(views.show_more_review),
        name="show-more-review",
    ),
    path(
        "like-to-review/", login_required(views.like_to_review), name="like-to-review"
    ),
    path("sku-to-buyout/", login_required(views.sku_to_buyout), name="sku-to-buyout"),
    path("get-latest-group/", views.get_last_group, name="get-latest-group"),
    re_path(r"^group-buyouts$", views.group_buyouts, name="group-buyouts"),
    path("get-payment-link/", views.get_payment_link, name="get-payment-link"),
    path("check-payed/", views.check_payed, name="check-payed"),
    path("set-sms-type/", views.set_sms_type, name="set-sms-type"),
    path("get-pay-link/", views.get_pay_link, name="get-pay-link"),
    path(
        "edit_review/<int:review_id>/",
        login_required(views.edit_review),
        name="edit-review",
    ),
    path("referral/", login_required(views.referral), name="referral"),
    path("set-bad-payed/", login_required(views.set_bad_payed), name="set-bad-payed"),
    path("personal-room/", login_required(views.personal_room), name="personal-room"),
    path(
        "general-information-update/",
        login_required(views.general_information_update),
        name="general-information-update",
    ),
    path(
        "password-update/",
        login_required(views.password_update),
        name="password-update",
    ),
    path(
        "generate-text-review/",
        login_required(views.generate_text_review),
        name="generate-text-review",
    ),
    path("good-feedbacks/", views.good_feedbacks, name="good-feedabacks"),
    path("checking-account/", b_views.checking_account, name="checking-account"),
    path("buyout-edit/", views.buyout_edit, name="buyout-edit"),
    path("buyout-group-delete/", views.buyout_group_delete, name="buyout-group-delete"),
    path("services/", views.services, name="services"),
    # Matches any html file
    # re_path(r'^.*\.*', views.pages, name='pages')
    
    
    
    
    path("projects/", views.projects, name="projects"),
    path("project-create/", views.project_create, name="project-create"),
    path("list-recipient/", views.list_recipient, name="list-recipient"),
    path("chat/", views.chat, name="chat"),
    path("channels/", views.channels, name="channels"),
    path("get-tochka-phone/", views.get_tochka_phone, name="get-tochka-phone"),

    
    path('templates/<str:page_name>/', views.dynamic_page),
]

# name - имя для path(), к нему можно обратиться из кода,
# чтобы установить ссылку на страницу сайта.
