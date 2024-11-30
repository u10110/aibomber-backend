# -*- encoding: utf-8 -*-
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.decorators.csrf import csrf_exempt

from apps.billing import views as b_views
from apps.home import views

urlpatterns = [
    path("", login_required(views.index), name="home"),
    path("upload/", login_required(views.upload), name="upload"),
    path("pricing/", login_required(views.pricing), name="pricing"),
    path(
        "account-billing/",
        login_required(views.account_billing),
        name="account-billing",
    ),
    path("add-question/", login_required(views.add_question), name="add-question"),
    path("add-to-cart/", login_required(views.add_to_cart), name="add-to-cart"),
    path(
        "add-to-waiting/", login_required(views.add_to_waiting), name="add-to-waiting"
    ),
    path("add-sms-cloud/", login_required(views.add_sms_cloud), name="add-sms-cloud"),
    path("get-tochka-phone/", views.get_tochka_phone, name="get-tochka-phone"),
    path(
        "add-card/<int:pk>/delete/",
        login_required(views.card_delete),
        name="card-delete",
    ),
    path("account/", login_required(views.account), name="account"),
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
    path("faq/", views.faq, name="faq"),
    path("lessons/", views.lessons, name="lessons"),
    path("set-sms-type/", views.set_sms_type, name="set-sms-type"),
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
    path("checking-account/", b_views.checking_account, name="checking-account"),
    path("services/", views.services, name="services"),
    
    
    path("projects/", views.projects, name="projects"),
    path('project-edit/<int:id>/', views.project_edit, name='project-edit'),
    path('projects/edit/<int:id>/', views.project_edit, name='project-edit'),

    path('project-start/<int:pk>/', views.project_start, name='project-start'),
    path('project-stop/<int:pk>/', views.project_stop, name='project-stop'),
    path('project-delete/<int:pk>/', views.project_delete, name='project-delete'),
    path('projects/toggle-active/', views.toggle_project_active, name='toggle-project-active'),
    path('channels/toggle-active/', views.toggle_channel_active, name='toggle-channel-active'),


    
    # path("project-create/", views.project_create, name="project-create"),
    
    path("list-recipient/", views.list_recipient, name="list-recipient"),
    path('list-recipient-delete/<int:pk>/', views.list_recipient_delete, name='list-recipient-delete'),
    path('save-recipients/', views.save_recipients, name='save_recipients'),

    path("channels/", views.channels, name="channels"),
    path('channel-start/<int:pk>/', views.channel_start, name='channel-start'),
    path('channel-stop/<int:pk>/', views.channel_stop, name='channel-stop'),
    path('channel-delete/<int:pk>/', views.channel_delete, name='channel-delete'),
    # path('channel-edit/<int:id>/', views.channel_edit, name='channel-edit'),

    
    
    path("chat/", views.chat, name="chat"),
    path('messages/', views.chat_messages, name='messages'),



    path("get-tochka-phone/", views.get_tochka_phone, name="get-tochka-phone"),

    
    path('templates/<str:page_name>/', views.dynamic_page),
]

