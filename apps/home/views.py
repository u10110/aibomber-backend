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
import re

from apps.alert.views import billing_check
from apps.authentication.models import UserInfo
from apps.billing.helper import Helper as BHelper
from apps.billing.models import Limits, Order, Paid, UnicTariff
from apps.users_control.models import ReferalCounter, UsersAgreement
from core.settings import MEDIA_ROOT

from .forms import *
from .helper import Helper
from .models import (
    ReferralClickCounter,
    ReferralUsers,
    ReferralLinks,
    ClientSettings,
    Channel,
    Chat,
    Phone,
    ChatMessages
)
from .module import *
from .services.services import MinioService
from django.shortcuts import get_object_or_404
from django.db.models import Max, OuterRef, Subquery, Count, Q, F
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

from django.shortcuts import render
from django.http import JsonResponse
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from .models import Project
from .services.gpt_assistant import GPTAssistant
from django.db.models import Count, Max, Subquery, OuterRef, IntegerField, Case, When


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
            "https://eliment.ai/amotest/",
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


def tariffs(request):
    tariffs = [
        {
            "name": "Тариф Базовый",
            "price_month": "8 333 ₽/мес.",
            "price_year": "100 000 ₽ в год",
            "users": "1 цифровой сотрудник",
            "storage": "Одна роль - лидоруб, работает через Telegram.",
            "duration": "1 год",
            "cost_per_employee": "8 333 ₽",
            "extra_employee_cost": "невозможно",
            "upgrade_option": "Возможно"
        },
        {
            "name": "Тариф Микробизнес",
            "price_month": "5 556 ₽/мес.",
            "price_year": "200 000 ₽ в год",
            "users": "3 цифровых сотрудника",
            "storage": """- 2 сотрудника: роль - лидоруб, работает через Telegram и WhatsApp.<br>
                          - 1 сотрудник: роль - обработка входящего трафика на Avito.""",
            "duration": "1 год",
            "cost_per_employee": "5 556 ₽",
            "extra_employee_cost": "8 500 ₽ (в месяц)",
            "upgrade_option": "Возможно в течение 3 месяцев после начала действия текущего тарифа"
        },
        {
            "name": "Тариф Компания",
            "price_month": "3 333 ₽/мес.",
            "price_year": "400 000 ₽ в год",
            "users": "10 цифровых сотрудников",
            "storage": """Первый продукт (5 сотрудников):<br>
                          - 3 сотрудника: роль - лидоруб, работает через Telegram, WhatsApp и VK.<br>
                          - 1 сотрудник: роль - обработка входящего трафика на Avito.<br>
                          - 1 сотрудник: роль - поддержка клиентов через Telegram.<br><br>
                          Второй продукт (5 сотрудников): аналогично.""",
            "duration": "1 год",
            "cost_per_employee": "3 333 ₽",
            "extra_employee_cost": "5 000 ₽ (в месяц)",
            "upgrade_option": "Возможно в течение 3 месяцев после начала действия текущего тарифа"
        },
        # {
        #     "name": "Тариф Индивидуальный",
        #     "price_month": "По согласованию",
        #     "price_year": "По согласованию",
        #     "users": "Индивидуальное количество сотрудников",
        #     "storage": "Возможность реализации на серверах клиента.",
        #     "duration": "от 1 года",
        #     "cost_per_employee": "-",
        #     "extra_employee_cost": "Индивидуально",
        #     "upgrade_option": "-"
        # }
    ]
    return render(request, 'apps/tariffs.html', {"tariffs": tariffs})


@csrf_exempt
def contact_request(request):
    if request.method == "POST":
        data = json.loads(request.body)
        phone_number = data.get("phone_number")
        Phone.objects.create(phone=phone_number)
        # Здесь можно сохранить номер в базу данных или отправить уведомление
        return JsonResponse({"message": "Спасибо за вашу заявку! Мы свяжемся с вами."})
    return JsonResponse({"error": "Некорректный запрос"}, status=400)




def projects(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, user=request.user)  # Передаём user для фильтрации
        if form.is_valid():
            project = form.save(commit=False)
            project.client = request.user  # Привязываем проект к текущему пользователю
            project.save()

            # Обновляем project_id для связанных каналов
            channels = form.cleaned_data.get('channel', [])
            for channel in channels:
                channel.project_id = project.id
                channel.save()

            # Обновляем project_id для связанных получателей
            recipients = form.cleaned_data.get('recipients', [])
            for recipient in recipients:
                recipient.project_id = project.id
                recipient.save()

            return redirect('/projects/')
    else:
        form = ProjectForm(user=request.user)  # Передаём user для фильтрации

    projects = Project.objects.filter(client=request.user)


    
    # Получаем все проекты из модели, принадлежащие текущему пользователю
    client_settings = ClientSettings.objects.get(client=request.user)
    current_balance = client_settings.balance
    # Передаем данные в шаблон
    context = {
        'form': form,
        'projects': projects,
        'current_balance': current_balance,
    }
    return render(request, 'apps/projects.html', context)


def project_create(request):
    agent_type = request.GET.get('type', None)
    max_files = 6
    uploaded_files = 0  # Если редактируется проект, здесь можно подсчитать уже загруженные файлы

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, user=request.user, agent_type=agent_type)  # Передаём user для фильтрации
        file_formset = ProjectFileFormSet(request.POST, request.FILES, queryset=ProjectFile.objects.none())

        if form.is_valid() and file_formset.is_valid():
            project = form.save(commit=False)
            project.client = request.user  # Привязываем проект к текущему пользователю
            # project.agent_type = agent_type
            project.save()

            # Обновляем project_id для связанных каналов
            channels = form.cleaned_data.get('channel', [])
            for channel in channels:
                channel.project_id = project.id
                channel.save()

            # Обновляем project_id для связанных получателей
            recipients = form.cleaned_data.get('recipients', [])
            for recipient in recipients:
                recipient.project_id = project.id
                recipient.save()
            
            for file_form in file_formset:
                if file_form.cleaned_data.get('file'):
                    project_file = file_form.save(commit=False)
                    project_file.project = project
                    project_file.save()


            return redirect('/projects/')
        else:
            print("Форма не прошла валидацию")
            print(form.errors)  # Печатает ошибки полей
            print(form.non_field_errors())  # Печатает общие ошибки
    else:

        form = ProjectForm(user=request.user)
        file_formset = ProjectFileFormSet(queryset=ProjectFile.objects.none())

    return render(request, 'apps/project_create.html', {'form': form, 'agent_type': agent_type, 'file_formset': file_formset, 'max_files': max_files, 'uploaded_files': uploaded_files,})



def project_edit(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()
            return redirect("projects")  # После успешного сохранения возвращаемся к списку проектов
    else:
        form = ProjectForm(instance=project)  # Предзаполняем форму данными проекта
    max_files = 6
    uploaded_files = 0  # Если редактируется проект, здесь можно 
    context = {
        "form": form,
        "project": project,
        "max_files": 6,
        "uploaded_files": 0
    }
    return render(request, "apps/project_create.html", context)


@csrf_exempt
def toggle_project_active(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')
            is_active = data.get('is_active')

            project = Project.objects.get(id=project_id, client=request.user)
            project.is_active = is_active
            project.save()

            return JsonResponse({'success': True, 'message': 'Состояние обновлено', 'is_active': project.is_active})
        except Project.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Проект не найден'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Неверный метод запроса'}, status=400)

def project_start(request, pk):
    project = get_object_or_404(Project, pk=pk, client=request.user)
    project.status = "active"  # Укажите соответствующее значение
    project.save()
    return redirect('projects')

def project_stop(request, pk):
    project = get_object_or_404(Project, pk=pk, client=request.user)
    project.status = "stopped"  # Укажите соответствующее значение
    project.save()
    return redirect('projects')

def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, client=request.user)
    Channel.objects.filter(project_id=project.id).update(project_id=None)
    Recipient.objects.filter(project_id=project.id).update(project_id=None)
    project.delete()
    return redirect('projects')


def channel_start(request, pk):
    project = get_object_or_404(Channel, pk=pk, client=request.user)
    project.status = "active"  # Укажите соответствующее значение
    project.save()
    return redirect('channels')

def channel_stop(request, pk):
    project = get_object_or_404(Channel, pk=pk, client=request.user)
    project.status = "stopped"  # Укажите соответствующее значение
    project.save()
    return redirect('channels')

def channel_delete(request, pk):
    project = get_object_or_404(Channel, pk=pk, client=request.user)
    project.delete()
    return redirect('channels')

@csrf_exempt
def toggle_channel_active(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        channel_id = data.get('channel_id')
        is_active = data.get('is_active')

        try:
            channel = Channel.objects.get(id=channel_id)
            channel.is_active = is_active
            channel.save()
            return JsonResponse({'success': True, 'channel_id': channel_id, 'is_active': is_active})
        except Channel.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Channel not found'}, status=404)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def list_recipient(request):

    if request.method == 'POST':
        form = RecipientForm(request.POST, request.FILES)
        if form.is_valid():
            recipient = form.save(commit=False)
            recipient.client = request.user
            recipient.save()

            return redirect('/list-recipient/')
    else:
        form = RecipientForm()

    # Получаем словарь project_id -> название проекта
    #project_titles = {project.id: project.title for project in Project.objects.filter(client=request.user)}

    # Аннотация для подсчета количества контактов
    recipients = Recipient.objects.filter(client=request.user).annotate(
        contact_count=Count('remote_ids')
    )

    # Аннотация для подсчета количества контактов, активных переписок, отправленных и оставшихся сообщений
    """
        
    projects = Chat.objects.filter(project=project).annotate(
        # Общее количество TG ID, связанных с получателем
        contact_count=Count('user_id', distinct=True),
        
        # Количество активных переписок
        active_conversations=Count(
            'chat_id',
            filter=Q(
                tg_id_set__tg_id__in=Subquery(
                    Chat.objects.filter(
                        client=request.user, 
                        message_type='message', 
                        user_id=OuterRef('tg_id_set__tg_id')
                    ).values('user_id')
                )
            ),
            distinct=True
        ),

        # Отправлено: количество TG ID в TgID таблице
        sent=Count('user_id', filter=Q(tg_id_set__is_auto_active=True), distinct=True),

        # Осталось: общее количество минус отправленные
        remaining=F('contact_count') - Count('chat_id', filter=Q(chat_id__is_auto_active=True), distinct=True),
    )
     """
    
    # Добавляем поле project_title в каждый объект
    """
    for project in projects:
        project.project_title = project_titles.get(project.project_id, "Не привязан")
        
        # Получаем список всех TG IDs, связанных с этим списком
        chat_ids = project.chat.values_list('chat_id', flat=True)  # Получаем только tg_id
        project.tg_ids = list(chat_ids)  # Преобразуем в список для передачи в шаблон
    """
    context = {
        'form': form,
        'lists': recipients,
    }
    return render(request, "apps/list_recipient.html", context)




def list_recipient_edit(request, id):
    recipient = get_object_or_404(Recipient, id=id, client=request.user)

    if request.method == 'POST': 
        form = RecipientForm(request.POST, instance=recipient)
        print(f" form {form}")
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        return JsonResponse({'success': False, 'message': 'Неверный метод запроса'})


def save_recipients(request):
    if request.method == 'POST':
        form = RecipientForm(request.POST)
        if form.is_valid():
            tg_ids = form.cleaned_data['tg_ids']
            print(f"tg_ids {tg_ids}")
            recipients = [
                Recipient(client=request.user, tg_id=tg_id) for tg_id in tg_ids
            ]
            Recipient.objects.bulk_create(recipients)  # Эффективно сохраняем список
            return redirect('/list-recipient/')
    else:
        form = RecipientForm()
    print(1)
    # return render(request, 'save_recipients.html', {'form': form})
    return render(request, 'apps\list_recipient.html', {'form': form})



def list_recipient_delete(request, pk):
    list_recipient = get_object_or_404(Recipient, pk=pk, client=request.user)
    list_recipient.delete()
    return redirect('list-recipient')


def get_context_data(request, user_id=None, chats=None, messages=None, current_chat=None):
    projects = Project.objects.filter(client_id=request.user.id)
    
    context = {
        'chats': chats,
        'messages': messages,
        'chat': current_chat,
        'projects': projects,  
    }
    return context


def chat(request):

    chat_id = request.GET.get('chat_id')
    user_id = request.user.id

    chat = Chat.objects.filter(
        id=chat_id
    ).first()



    chats = Chat.objects.filter(
        id=chat_id
    ).values(
        'user_id'
    )

    current_messages = []

    if chat:
        current_messages = ChatMessages.objects.filter(
            chat_id=chat_id,
        ).order_by('created_at')

    context = get_context_data(request, user_id, chats, current_messages, chat)

    return render(request, "apps/chat.html", context)

def chat_messages(request):
    chat_id = request.GET.get('chat_id', None)
    user_id =  request.GET.get('user_id', None)
    
    if request.method == "POST":
        user_message = request.POST.get('user_message')
        if user_message:
            current_chat = Chat.objects.filter(id=chat_id).first()
            if current_chat:

                payload = json.dumps({
                "phone": current_chat.user_name,
                "username": user_id,
                "message": user_message
                })
                headers = {
                'Content-Type': 'application/json'
                }
                response = requests.post(
                    f"{FASTAPI_URL}/send-message/",
                    headers=headers,
                    data=payload
                )
                print(response.text)
                print(
                    user_id,
                    current_chat.user_name,
                    current_chat.client_id,
                    user_message,
                )
                ChatMessages.objects.create(
                    chat_id=chat_id,
                    user_name=current_chat.user_name,
                    client_id=current_chat.client_id,
                    user_message=user_message,
                    message_type='anwser',  # Изменено на 'question'
                )
            return redirect(f'{reverse("messages")}?user_id={user_id}')

    chats = Chat.objects.filter(
        client_id=request.user.id
    ).order_by('-last_message_time')

    messages = []
    current_chat = None
    if user_id:
        messages = ChatMessages.objects.filter(
            chat_id=chat_id
        ).order_by('created_at')

    context = get_context_data(request, user_id, chats, messages, current_chat)

    return render(request, 'apps/chat.html', context)





def channels(request):
    if request.method == 'POST':
        form = ChannelForm(request.POST, initial={'client': request.user})
        print(1)
        if form.is_valid():
            channels = form.save()  # Сохраняем все записи
            return redirect('/channels/')
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            

    else:
        form = ChannelForm(request.POST, initial={'client': request.user})


    # Получаем все проекты из модели
    projects = Channel.objects.filter(client=request.user)
    
    project_titles = {project.id: project.title for project in Project.objects.filter(client=request.user)}

    # Добавляем название проекта к каждому каналу
    for channel in projects:
        channel.project_title = project_titles.get(channel.project_id, "Не привязан")


    # Передаем данные в шаблон
    context = {
        'form': form,
        'channels': projects,
    }
    return render(request, 'apps/channels.html', context)




BASE_URL = "https://my.telegram.org"

def create_app_internal(session):
    """
    Внутренняя функция для создания приложения.
    Используется из verify_code.
    """
    try:
        response = session.post(
            f"{BASE_URL}/apps/create",
            data={
                'app_title': 'Eliment',  # Название приложения
                'app_shortname': 'eliment_app',  # Уникальное имя
                'app_platform': 'desktop',  # Можно заменить на web/other
                'app_url': '',  # URL приложения, если есть
                'app_desc': '',  # Описание приложения
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if response.status_code == 200:
            response_data = response.json()
            return {
                'success': True,
                'api_id': response_data.get('api_id'),
                'api_hash': response_data.get('api_hash'),
            }
        else:
            return {
                'success': False,
                'error': 'Ошибка при создании приложения на стороне Telegram.',
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }



@csrf_exempt
def create_app(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        app_title = data.get('title', 'eliment')
        app_shortname = data.get('shortname', 'eliment_app')

        try:
            # Извлекаем сохраненную сессию
            session = requests.Session()
            session.cookies.update(request.session.get('tg_session', {}))

            # Отправляем запрос на создание приложения
            response = session.post(
                f"{BASE_URL}/apps/create",
                data={
                    'app_title': app_title,
                    'app_shortname': app_shortname,
                    'app_platform': 'desktop',  # Можно заменить на web/other
                    'app_url': '',  # URL приложения, если есть
                    'app_desc': '',  # Описание приложения
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if response.status_code == 200:
                # Парсим `API_ID` и `API_HASH` из ответа
                api_id = response.json().get('api_id')
                api_hash = response.json().get('api_hash')
                return JsonResponse({'success': True, 'api_id': api_id, 'api_hash': api_hash})
            else:
                return JsonResponse({'success': False, 'error': 'Ошибка при создании приложения.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def toggle_auto_active(request, chat_id):
    if request.method == 'POST':
        try:
            # Получаем данные из тела запроса
            data = json.loads(request.body)
            is_auto_active = data.get('is_auto_active')

            if is_auto_active is None:
                return JsonResponse({'error': 'is_auto_active is required'}, status=400)

            # Получаем объекты Chat и TgID
            chat = get_object_or_404(Chat, id=chat_id)
            tg = get_object_or_404(TgID, tg_id=chat.user_id)  # Предполагается связь через user_id

            # Обновляем значения is_auto_active
            tg.is_auto_active = is_auto_active
            tg.save()

            chat.is_auto_active = is_auto_active
            chat.save()

            return JsonResponse({'is_auto_active': chat.is_auto_active})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def change_status(request, chat_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        new_status = data.get('status')

        chat = Chat.objects.get(id=chat_id)
        chat.status = new_status
        chat.save()

       # tg_id = TgID.objects.get(tg_id=chat.user_id)
       # tg_id.status = new_status
       # tg_id.save()

        return JsonResponse({'status': chat.status})
    return JsonResponse({'error': 'Invalid request method'}, status=400)



# FASTAPI_URL = "http://fastapi_app:8001"  # URL FastAPI-сервиса (имя сервиса в Docker)
# FASTAPI_URL = "http://127.0.0.1:8001"  # URL FastAPI-сервиса (имя сервиса в Docker)
FASTAPI_URL = "http://91.197.96.240:8001"  # URL FastAPI-сервиса (имя сервиса в Docker)


@csrf_exempt
def send_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone')

            if not phone_number:
                return JsonResponse({"message": "Номер телефона не указан", "success": False})

            phone_number = re.sub(r'[^\d+]', '', phone_number.strip())
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number  # Добавляем '+' в начало, если его нет

            print(phone_number)
            # Отправка запроса в FastAPI
            response = requests.post(
                f"{FASTAPI_URL}/send-code/",
                params={"phone": phone_number},
            )
            
            if response.status_code == 200:
                return JsonResponse(response.json())
            else:
                return JsonResponse({"message": response.text, "success": False}, status=response.status_code)
        except Exception as e:
            return JsonResponse({"message": str(e), "success": False})

    return JsonResponse({"message": "Метод запроса должен быть POST", "success": False})




# Шаг 2: Подтверждаем код авторизации
@csrf_exempt
def verify_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone')
            code = data.get('code')

            if not phone_number or not code:
                return JsonResponse({"message": "Номер телефона или код не предоставлены", "success": False})

            # Отправка запроса в FastAPI
            print({"phone": phone_number, "code": code})
            response = requests.post(
                f"{FASTAPI_URL}/verify-code/",
                json={"phone": phone_number, "code": code},
            )
            
            if response.status_code == 200:
                # Если успех, обновляем статус в базе данных
                channel, created = Channel.objects.get_or_create(phone=phone_number)
                channel.status = 'authorized'
                channel.save()

                return JsonResponse(response.json())
            else:
                return JsonResponse({"message": response.text, "success": False}, status=response.status_code)
        except Exception as e:
            return JsonResponse({"message": str(e), "success": False})

    return JsonResponse({"message": "Метод запроса должен быть POST", "success": False})





@csrf_exempt
def create_project_chat(request):
    """
    Обрабатывает запросы чата на этапе создания проекта.
    """
    if request.method == "POST":
        try:
            # Парсим данные формы
            data = json.loads(request.body)
            project = Project(
                id=None,
                title=data.get("title"),
                agent_type=data.get("agent_type"),
                work_option=data.get("work_option"),
                gpt_version=int(data.get("gpt_version")),
                knowledge_base_text=data.get("knowledge_base_text"),
                hello_text=data.get("hello_text"),
                prompt=data.get("prompt"),
            )

            # Форматируем историю чата
            chat_history = data.get("chat_history", [])
            formatted_history = []

            # Форматируем историю чата
            for item in chat_history:
                question = item.get("question")
                response = item.get("response")
                if question and response:  # Проверяем, что есть и вопрос, и ответ
                    formatted_history.append({"role": "user", "content": question})
                    formatted_history.append({"role": "assistant", "content": response})

            # Ограничиваем длину истории (например, 10 пар сообщений)
            formatted_history = formatted_history[-20:]  # 10 вопросов и 10 ответов


            # Инициализируем GPTAssistant с историей чата
            assistant = GPTAssistant(project)
            # Передаём историю в GPTAssistant
            assistant.chat_history = formatted_history

            # Получаем вопрос
            print(assistant.chat_history)
            question = data.get("question")
            if not question:
                return JsonResponse({"error": "Вопрос не предоставлен."}, status=400)
            print(question)
            # Получаем ответ от GPT
            response = assistant.ask_question(question, False)

            return JsonResponse({
                "question": question,
                "response": response
            }, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Метод не поддерживается."}, status=405)





@csrf_exempt
def gpt_assistant(request):
    """
    Эндпоинт для взаимодействия с GPTAssistant.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

    # Получение user_id, project_id и question из тела запроса
    tgid_id = request.POST.get('tgid_id')
    project_id = request.POST.get('project_id')
    question = request.POST.get('question')
    
    channel_phone = request.POST.get('channel_phone')
    user_id = request.POST.get('user_id')

    if not project_id:
        return JsonResponse({"error": "Missing required parameters: user_id, project_id, or question"}, status=400)

    # Получение объекта проекта
    project = get_object_or_404(Project, id=project_id)
    print(project)

    # Создание экземпляра GPTAssistant
    assistant = GPTAssistant(project=project, tgid_id=tgid_id, channel_phone=channel_phone, user_id=user_id)

    # Получение ответа от GPT
    try:
        answer = assistant.ask_question(question)
        return JsonResponse({"anwser": answer})
    except Exception as e:
        return JsonResponse({"error": f"Failed to process the request: {str(e)}"}, status=500)
    
    
    

@csrf_exempt
def validate_google_link(request):
    """
    Проверяет, является ли предоставленная ссылка действительной Google-ссылкой.
    """
    if request.method == "POST":
        link = request.POST.get("link", "").strip()
        if not link:
            return JsonResponse({"valid": False, "message": "Ссылка не указана."})

        # Проверяем, начинается ли ссылка с Google-домена
        if not link.startswith("https://docs.google.com/"):
            return JsonResponse({"valid": False, "message": "Ссылка должна быть Google-документом."})

        # Проверяем доступность ссылки
        try:
            response = requests.head(link, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                return JsonResponse({"valid": True, "message": "Ссылка валидна."})
            else:
                return JsonResponse({"valid": False, "message": "Ссылка недоступна."})
        except requests.RequestException as e:
            return JsonResponse({"valid": False, "message": f"Ошибка проверки: {str(e)}"})

    return JsonResponse({"valid": False, "message": "Некорректный метод запроса."})


@csrf_exempt
def save_google_link(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            google_doc = data.get('google_doc')
            project_id = data.get('project_id')

            if not google_doc or not project_id:
                return JsonResponse({'success': False, 'message': 'Неверные данные'})

            project = Project.objects.get(id=project_id)
            project.google_doc = google_doc
            project.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Только POST-запросы'})