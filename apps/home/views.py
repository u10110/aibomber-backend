import codecs
import csv
import datetime
import hashlib
import json
import locale
import random
import re
import string
import time
from calendar import c
from datetime import timedelta, timezone
from http import client
from io import BytesIO
from multiprocessing import context
from sqlite3 import IntegrityError
from struct import pack_into
from urllib import response

import numpy as np
import requests
import xlsxwriter
from django import template
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.db.utils import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template import loader
from django.urls import path, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DeleteView
from loguru import logger
from lxml import html
from sentry_sdk import last_event_id

from apps.alert.views import billing_check
from apps.authentication.models import UserInfo
from apps.billing.helper import Helper as BHelper
from apps.billing.models import Limits, Order, Paid, UnicTariff
from apps.users_control.models import ReferalCounter, UsersAgreement
from core.settings import MEDIA_ROOT

from .forms import *
from .helper import Helper
from .models import (
    ClientSettings,
)
from .module import *
from .services.services import MinioService
from .WB_token import X64ApiClient


def error(request):
    return render(request, "errors/technical_break.html")

def dynamic_page(request,page_name):
    return render(request, f'home/{page_name}.html')




def password_update(request):
    if request.method == "POST":
        data = request.POST
        print(data)
        user = request.user
        if user.check_password(data["password-current"]):
            if data["password-new"] == data["password-confirm"]:
                user.set_password(data["password-new"])
                user.save()
                update_session_auth_hash(request, user)
                return JsonResponse({"resp": "ok"}, status=200)
            else:
                return JsonResponse({"resp": "password not mutch"}, status=200)
        else:
            return JsonResponse({"resp": "bad password"}, status=200)


def general_information_update(request):
    if request.method == "POST":
        data = request.POST
        print(data)
        mail_agree = True if "mailingOnPhoneNumber" in data else False
        phone_agree = True if "mailingOnMail" in data else False
        UsersAgreement.objects.filter(client=request.user).update(
            mail_agree=mail_agree, phone_agree=phone_agree
        )
        user = User.objects.get(id=request.user.id)
        user.first_name = data["name"]
        user.last_name = data["surname"]
        user.email = data["email"]
        user.save()
        user_info = UserInfo.objects.get(user=request.user)
        if data["sex"] == "Мужчина":
            user_info.sex = 1
        elif data["sex"] == "Женщина":
            user_info.sex = 0
        if "year" in data:
            if int(data["year"]) < 2010:
                user_info.date_birthday = datetime.date(
                    year=int(data["year"]),
                    month=int(data["month"]) + 1,
                    day=int(data["day"]),
                )

        user_info.save()
        r = requests.post(
            "https://app.mplab.io/amotest/",
            json={"client_id": request.user, "type_deal": "user_d_add"},
            timeout=10,
        )
        if r.status_code == 200:
            print(f"amo {r.text}")

        return JsonResponse({"resp": "ok"}, status=200)


def personal_room(request):
    context = {}
    user_info = {}
    user = request.user
    if UserInfo.objects.filter(user=user).exists():
        info_user = UserInfo.objects.get(user=user)
    else:
        info_user = UserInfo.objects.create(user=user)
    if UsersAgreement.objects.filter(client=user):
        info_agreement = UsersAgreement.objects.get(client=user)
    else:
        info_agreement = UsersAgreement.objects.create(client=user)
    user_info["name"] = user.first_name
    user_info["surname"] = user.last_name
    user_info["email"] = user.email
    user_info["phone"] = user.phone
    user_info["sex"] = info_user.sex
    user_info["phone_agree"] = info_agreement.phone_agree
    user_info["mail_agree"] = info_agreement.mail_agree
    if info_user.date_birthday:
        user_info["year"] = info_user.date_birthday.year
        user_info["month"] = info_user.date_birthday.month
        user_info["day"] = info_user.date_birthday.day
    user_info["tg_token"] = ClientSettings.objects.get(client=user).tg_token
    api_tokens = Client_Supplier_Access.objects.filter(
        client_settings=ClientSettings.objects.get(client=request.user)
    )
    context["user_info"] = user_info

    date_now = datetime.datetime.now(timezone.utc)
    if Limits.objects.filter(
        client=user, start_date__lte=date_now, end_date__gte=date_now
    ).exists():
        user_limits = {}
        limits = Limits.objects.filter(
            client=user, start_date__lte=date_now, end_date__gte=date_now
        )[0]
        order = limits.paid_info.order

        if order.is_calculated == True:
            tariff_info = order.calculated_tariff
        else:
            tariff_info = UnicTariff.objects.get(title=order.tariff)

        if order.is_calculated == True:
            user_limits["tariff"] = "Собственный"
        else:
            if tariff_info.title == "showroom":
                user_limits["tariff"] = "Шоурум"
            elif tariff_info.title == "market":
                user_limits["tariff"] = "Магазин"
            elif tariff_info.title == "hypermarket":
                user_limits["tariff"] = "Гипермаркет"
            elif tariff_info.title == "magigrand":
                user_limits["tariff"] = "Магигранд"
            else:
                user_limits["tariff"] = tariff_info.title
        for_max_limits = BHelper(user.id)
        user_limits["course_autobuy"] = for_max_limits.get_max_limit("course_autobuy")
        user_limits["monitor"] = for_max_limits.get_max_limit("monitor")
        user_limits["buyout_limit"] = limits.buyout_limit
        user_limits["buyout_limit_max"] = for_max_limits.get_max_limit("buyout_limit")
        user_limits["review_limit"] = limits.review_limit
        user_limits["review_limit_max"] = for_max_limits.get_max_limit("review_limit")
        user_limits["like_limit"] = limits.like_limit
        user_limits["like_limit_max"] = for_max_limits.get_max_limit("like_limit")
        user_limits["like_review_limit"] = limits.like_review_limit
        user_limits["like_review_max"] = for_max_limits.get_max_limit(
            "like_review_limit"
        )
        user_limits["question_limit"] = limits.question_limit
        user_limits["question_limit_max"] = for_max_limits.get_max_limit(
            "question_limit"
        )
        user_limits["positions_limit"] = get_count_search_promotion_limits(
            user.id, is_search_promotion=False
        )
        user_limits["positions_limit_max"] = get_search_promotion_limits(
            user.id, is_search_promotion=False
        )
        user_limits["search_promotion_limit"] = get_count_search_promotion_limits(
            user.id, is_search_promotion=True
        )
        user_limits["search_promotion_limit_max"] = get_search_promotion_limits(
            user.id, is_search_promotion=True
        )
        user_limits["course_autobuy"] = for_max_limits.get_max_limit("course_autobuy")
        user_limits["monitoring_rate"] = for_max_limits.get_max_limit("monitoring_rate")
        user_limits["tariff_date_end"] = limits.paid_info.end_date
        context["limits"] = user_limits

        tokens = Client_tokens.objects.filter(client=request.user).order_by(
            "created_at"
        )
        context["tokens"] = tokens

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        context["user_ip"] = ip

    else:
        pass
    print(api_tokens)
    if api_tokens:
        context["api_tokens"] = {
            "api_token_64": api_tokens[0].api_token_64,
            "api_token_new": api_tokens[0].api_token_new,
            "supplier_id": api_tokens[0].supplier_id,
        }
    print(context)
    return render(request, "apps/personal_room.html", context)


def set_bad_payed(request):
    date_now = datetime.datetime.now(datetime.timezone.utc)
    products = ProductBuyout.objects.filter(
        client_id=request.user, payment_status="pay_await", status="active"
    )
    for product in products:
        if (product.pay_link_generated + timedelta(seconds=300)) < date_now:
            ProductBuyout.objects.filter(id=product.id).update(payment_status="bad_pay")
            # limits = Limits.objects.get(
            #     client_id=request.user, start_date__lte=date_now, end_date__gte=date_now
            # )
            # limits.buyout_limit += 1
            # limits.save()
    return JsonResponse({"resp": True})


def referral(request):
    context = {}
    if not ReferralLinks.objects.filter(referrer=request.user).exists():
        while True:
            code = "".join(random.choice(string.ascii_letters) for x in range(10))
            if not ReferralLinks.objects.filter(code=code).exists():
                ReferralLinks.objects.create(code=code, referrer=request.user)
                break
    referral_object = ReferralLinks.objects.get(referrer=request.user)
    code = referral_object.code
    referral_link = f'{request.META["HTTP_HOST"]}/signup' + "?referrer=" + code
    count_click = len(ReferralClickCounter.objects.filter(source=referral_object))
    users_signup = ReferralUsers.objects.filter(source=referral_object)
    count_signup = len(users_signup)
    conter_paid = 0
    earned = 0
    objects = []
    if not ReferalCounter.objects.filter(client=request.user):
        ReferalCounter(client=request.user, balance=0).save()
    refferal_owner = ReferalCounter.objects.get(client=request.user)
    for user in users_signup:
        if Order.objects.filter(client=user.user, paid_status=True).exists():
            conter_paid += 1
        if not referal_live(refferal_owner.privileged, user.user.date_joined):
            continue
        orders = Order.objects.filter(client=user.user, paid_status=True, refered=False)
        earned += get_earned_referal(objects, refferal_owner.bonus, orders)
        if not refferal_owner.privileged or not orders:
            continue
        referral_object = ReferralLinks.objects.filter(referrer=user.user)
        if not referral_object:
            continue
        users_signup_sub = ReferralUsers.objects.filter(source=referral_object[0])
        for user_sub in users_signup_sub:
            if Order.objects.filter(client=user_sub.user, paid_status=True).exists():
                conter_paid += 1
            if not referal_live(refferal_owner.privileged, user_sub.user.date_joined):
                continue
            orders = Order.objects.filter(
                client=user_sub.user, paid_status=True, refered=False
            )
            earned += get_earned_referal(objects, refferal_owner.sub_bonus, orders)

    ReferalCounter.objects.filter(client=request.user).update(balance=earned)
    if refferal_owner.privileged:
        context["bonus_2level"] = refferal_owner.sub_bonus
    context["bonus"] = refferal_owner.bonus
    context["link"] = referral_link
    context["code"] = code
    context["count_click"] = count_click
    context["count_signup"] = count_signup
    context["conter_paid"] = conter_paid
    context["earned"] = int(earned)
    context["objects"] = objects

    return render(request, "apps/referral.html", context)


def set_sms_type(request):
    if request.method == "POST":
        num_group = request.POST["num_group"]
        sms_type = request.POST["sms_type"]
        print(sms_type)
        start_time = None
        end_time = None
        if sms_type == "tg" or sms_type == "tgsbp":
            start_time = request.POST["start_time"]
            end_time = request.POST["end_time"]
        ProductBuyout.objects.filter(
            client_id=request.user.id, num_group=num_group
        ).update(pay_type=sms_type, tg_start_date=start_time, tg_end_date=end_time)
    return JsonResponse({"resp": "ok"}, status="200")

def faq(request):
    return render(request, "apps/faq.html")


def lessons(request):
    class Object(object):
        pass

    if not request.user.id or not BHelper(request.user.id).get_max_limit(
        "course_autobuy"
    ):
        return HttpResponseRedirect("/")
    request2 = Object()
    request2.method = "POST"
    request2.body = str({"id": request.user.id}).replace("'", '"')
    response = billing_check(request2)
    response = json.loads(response._container[0])
    is_tariff = response["result"]
    return render(request, "apps/lessons.html", {"is_tariff": json.dumps(is_tariff)})



def pricing(request):
    context = {}
    date_now = datetime.datetime.now(datetime.timezone.utc)
    if Paid.objects.filter(client=request.user).exists():
        if (
            Paid.objects.filter(client=request.user).latest("end_date").end_date
            >= date_now.date()
        ):
            context["have_subscribe"] = True
    if "have_subscribe" not in context:
        context["have_subscribe"] = False
    return render(request, "apps/pricing.html", context)


def account_billing(request):
    return render(request, "apps/account-billing.html")


def review_rating(request):
    pass


def account(request):
    user = get_user_model().objects.get(id=request.user.id)
    context = {}
    if request.method == "POST":
        form = Account(request.POST)
        if form.is_valid():
            try:
                data = {
                    "first_name": form.cleaned_data.get("first_name"),
                    "last_name": form.cleaned_data.get("last_name"),
                    "phone": request.user.phone,
                    "email": form.cleaned_data.get("email"),
                    "password1": form.cleaned_data.get("password1"),
                }
                if data["first_name"]:
                    user.first_name = data["first_name"]
                if data["last_name"]:
                    user.last_name = data["last_name"]
                    user.phone = data["phone"]
                if data["email"]:
                    user.email = data["email"]
                if data["password1"]:
                    user.set_password(data["password1"])
                user.save()
                context["error"] = "False"
            except IntegrityError as e:
                context["error"] = True
                context[
                    "error_message"
                ] = "Пользователь с данным номером телефона уже зарегистрирован"

            # user.first_name = data['first_name']
            # user.last_name = data['last_name']
            # user.phone = data['phone']
            # user.email = data['email']
            # user.set_password(data['password1'])
            # user.save()
        else:
            # print(form.errors['phone'])
            print(list(dict(form.errors).keys())[0])
            error = list(dict(form.errors).keys())[0]
            context["error"] = True
            if error == "phone":
                context["error_message"] = "Неверный формат телефона"
            elif error == "password2":
                context["error_message"] = "Пароли не совпадают"

    else:
        form = Account(
            {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "email": user.email,
            }
        )
        tg_user_row = ClientSettings.objects.get(client=request.user.id)
        context["tg_token"] = tg_user_row.tg_token
    context["form"] = form
    return render(request, "apps/account.html", context=context)




def upload(request):
    if request.method == "POST" and request.FILES.get("file"):
        # upload = request.FILES['upload']
        print(request.FILES.get("file"))
        upload = request.FILES.get("file")
        fss = FileSystemStorage()
        file = fss.save(upload.name, upload)
        file_url = fss.url(file)
        return render(request, "main/upload.html", {"file_url": file_url})
    return render(request, "main/upload.html")


def auto_pay_stop(request, group):
    logged_in_user = request.user
    ProductBuyout.objects.filter(client_id=logged_in_user.id).filter(
        num_group=group
    ).update(pay_type="no")
    return HttpResponseRedirect(f"/buyout?status=active&group={group}")



def add_question(request):
    return render(request, "apps/add-question.html")


def add_to_cart(request):
    return render(request, "apps/add-to-cart.html")


def add_to_waiting(request):
    return render(request, "apps/add-to-waiting.html")



def index(request):
    print(Helper.get_client_ip(request))
    return HttpResponseRedirect(reverse('projects'))


def add_sms_cloud(request):
    logged_in_user = request.user
    if request.method == "POST":
        form = ClientSettingsForm(request.POST)
        if form.is_valid():
            data = {
                "sms_cloud": form.cleaned_data.get("sms_cloud"),
            }
            print(data)
            new_sms_cloud = ClientSettings.objects.update_or_create(
                {"sms_cloud": data["sms_cloud"], "client_id": logged_in_user.id},
                client_id=logged_in_user.id,
            )
        else:
            context = {}
            context["error"] = True
            context["error_message"] = "Неверная ссылка на облако"
            return render(request, "apps/add-card.html", context)
    return HttpResponseRedirect("/add-card/")


def get_tochka_phone(request):
    logged_in_user = request.user
    if request.method == "POST":
        usage_phones = {}
        for i in TochkaNumbers.objects.all():
            usage_phones[i.id] = 0
        for i in ClientSettings.objects.all():
            if i.tochka_number:
                usage_phones[i.tochka_number.id] += 1
        common_value = sorted(usage_phones, key=usage_phones.get)[0]
        cs = ClientSettings.objects.get(client=logged_in_user)
        tn = TochkaNumbers.objects.get(id=common_value)
        cs.tochka_number = tn
        cs.save()
    return HttpResponseRedirect("/add-card/")


def card_delete(request, pk):
    ClientCard.objects.filter(id=pk, client=request.user.id).delete()
    return HttpResponseRedirect("/add-card/")


def error_404(request, exception):
    return render(request, "apps/page-404.html")


def error_500(request, *args, **argv):
    return render(
        request,
        "apps/page-500.html",
        {"sentry_event_id": last_event_id(), "email": "anonymous@gmail.ru"},
        status=500,
    )



def get_segment(request):
    try:

        segment = request.path.split("/")[-1]
        active_menu = None

        if segment == "" or segment == "index.html":
            segment = "index"
            active_menu = "dashboard"

        if segment.startswith("dashboards-"):
            active_menu = "dashboard"

        if (
            segment.startswith("account-")
            or segment.startswith("users-")
            or segment.startswith("profile-")
            or segment.startswith("projects-")
        ):
            active_menu = "pages"

        if (
            segment.startswith("notifications")
            or segment.startswith("sweet-alerts")
            or segment.startswith("charts.html")
            or segment.startswith("widgets")
            or segment.startswith("pricing")
        ):
            active_menu = "pages"

        return segment, active_menu

    except:
        return "index", "dashboard"



    
def services(request):
    return render(request, "apps/services.html")




def projects(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('success_page')  # Замените 'success_page' на нужный URL
    else:
        form = ProjectForm()

    # Получаем все проекты из модели
    projects = Project.objects.all()

    # Передаем данные в шаблон
    context = {
        'form': form,
        'projects': projects,
    }
    return render(request, 'apps/projects.html', context)
    # return render(request, 'apps/projects.html', {'form': form})

def project_start(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.status = "active"  # Укажите соответствующее значение
    project.save()
    return redirect('projects')

def project_stop(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.status = "stopped"  # Укажите соответствующее значение
    project.save()
    return redirect('projects')

def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    project.delete()
    return redirect('projects')

def project_create(request):
    return render(request, "apps/project_create.html")

def list_recipient(request):
    return render(request, "apps/list_recipient.html")

def chat(request):
    return render(request, "apps/chat.html")

def channels(request):
    return render(request, "apps/channels.html")
