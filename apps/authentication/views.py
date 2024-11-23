# -*- encoding: utf-8 -*-
# Create your views here.
import datetime
import json
import os
import random
import re
import string
import urllib.parse
from codecs import unicode_escape_decode
from dataclasses import dataclass
from datetime import date, timedelta
from secrets import token_hex
from urllib import request

import requests
from decouple import config
from django.conf import settings

# from django.contrib.auth.models import User
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.sites.shortcuts import get_current_site
from django.core import serializers

# from django.utils.encoding import force_bytes
from django.core.mail import EmailMessage

# from django.utils.timezone import now
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.encoding import force_str as force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt

from apps.billing.models import Limits, Order, Paid, UnicTariff
from apps.home.helper import Helper
from apps.home.models import (
    ClientSettings,
    ReferralClickCounter,
    ReferralLinks,
    ReferralUsers,
)
from apps.home.services import amocrm

from .forms import LoginForm, SignUpForm
from .models import User
from .tokens import account_activation_token
from django.utils.decorators import method_decorator

from django_telegram_login.authentication import verify_telegram_authentication
from django.views import View


from django_telegram_login.widgets.generator import create_redirect_login_widget


@method_decorator(csrf_exempt, name='dispatch')
class LoginCallbackView(View):
    def post(self, request, *args, **kwargs):
        data = request.POST
        if verify_telegram_authentication(data):
            # Вход успешен
            return JsonResponse({"status": "success", "data": data})
        return JsonResponse({"status": "error", "message": "Invalid data"})



def legal(request):
    path = os.path.join(settings.MEDIA_ROOT, "docs", "Пользовательское соглашение.pdf")
    path
    print(path)
    with open(path, "rb") as pdf:
        response = HttpResponse(pdf.read(), content_type="application/pdf")
        response[
            "Content-Disposition"
        ] = "inline;filename=Пользовательское соглашение.pdf"
        return response


def privacy(request):
    path = os.path.join(settings.MEDIA_ROOT, "docs", "Политика конфиденциальности.pdf")
    path
    print(path)
    with open(path, "rb") as pdf:
        response = HttpResponse(pdf.read(), content_type="application/pdf")
        response[
            "Content-Disposition"
        ] = "inline;filename=Политика конфиденциальности.pdf"
        return response


def policy(request):
    path = os.path.join(settings.MEDIA_ROOT, "docs", "Политика оплаты и возврата.pdf")
    path
    print(path)
    with open(path, "rb") as pdf:
        response = HttpResponse(pdf.read(), content_type="application/pdf")
        response[
            "Content-Disposition"
        ] = "inline;filename=Политика оплаты и возврата.pdf"
        return response


def is_ajax(request):
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def login_view(request):
    form = LoginForm(request.POST or None)

    msg = None
    # auth_widget = create_redirect_login_widget(
    #     bot_name='eliment_test12312312312_bot',
    #     size='large',
    #     corner_radius="10",
    #     # data-onauth="onTelegramAuth"
    #     # data-button-title="Войти с Telegram"
    #     # redirect_url='http://127.0.0.1:8000/telegram/callback/'
    #     redirect_url='https://fa9f-91-197-106-185.ngrok-free.app/telegram/callback/'
    # )
    auth_widget = '<script async src="https://telegram.org/js/telegram-widget.js?3" ' \
              'data-telegram-login="eliment_test12312312312_bot" ' \
              'data-size="large" ' \
              'data-radius="10" ' \
              'data-auth-url="https://fa9f-91-197-106-185.ngrok-free.app/telegram/callback/" ' \
              'data-request-access="write"></script>'

    
    if is_ajax(request=request) and request.method == "POST":
        if form.is_valid():
            phone = form.cleaned_data.get("phone")
            password = form.cleaned_data.get("password")
            phone = (
                phone.replace("(", "")
                .replace(")", "")
                .replace("-", "")
                .replace(" ", "")
            )
            if phone.startswith("8"):
                phone = "+7" + phone[1:]
            user = authenticate(phone=phone, password=password)
            if (
                not User.objects.filter(phone=phone).exists()
                or User.objects.get(phone=phone).is_active == False
            ):
                return JsonResponse({"instance": "not_reg"}, status=400)
            if (user is not None) and user.is_active:
                login(request, user)
                return JsonResponse({"instance": "redirect"}, status=200)
            else:
                msg = "Invalid credentials"
                return JsonResponse({"instance": "bad"}, status=400)
        else:
            print(form.errors)
            msg = "Error validating the form"

    return render(request, "accounts/login.html", {"form": form, "msg": msg, 'auth_url_to_handle_telegram': auth_widget})


def register_user(request):
    referrer = request.GET.get("referrer", "")
    if referrer and ReferralLinks.objects.filter(code=referrer).exists():
        referrer_object = ReferralLinks.objects.get(code=referrer)
        ip = Helper.get_client_ip(request)
        ReferralClickCounter.objects.update_or_create(ip=ip, source=referrer_object)

    form = SignUpForm(request.POST or None)

    if is_ajax(request=request) and request.method == "POST":
        phone = request.POST["phone"]
        phone = (
            phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
        )
        if phone.startswith("8"):
            phone = "+7" + phone[1:]
        form = SignUpForm(
            request.POST or None,
            instance=User.objects.get(phone=phone)
            if User.objects.filter(phone=phone).exists()
            else None,
        )
        if form.is_valid():
            phone = form.cleaned_data.get("phone")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(phone=phone, password=raw_password)
            user = form.save(commit=False)
            code = "".join(["{}".format(random.randint(0, 9)) for num in range(0, 6)])
            print(code)
            user.code = urlsafe_base64_encode(force_bytes(code))
            user.last_sms_date = datetime.datetime.now(datetime.timezone.utc)
            user.is_active = False
            user.set_password(raw_password)
            if User.objects.filter(phone=phone).exists():
                old_signup = User.objects.get(phone=phone)
            else:
                old_signup = False
            if old_signup and old_signup.is_active == False:
                minutes = (
                    user.last_sms_date - old_signup.last_sms_date
                ).total_seconds() / 60
                print("difference", minutes)
                old_signup.code = urlsafe_base64_encode(force_bytes(code))
                old_signup.last_sms_date = datetime.datetime.now(datetime.timezone.utc)
                old_signup.save()
                text = f"Для регистрации на платформе введите код {code}"
                print(urllib.parse.quote_plus(text))
                params = {
                    "api_id": "8A5263F5-F81D-6A7C-B87E-C36C7B10AD93",
                    "to": [phone],
                    "from": "MP LAB",
                    "msg": text,
                    "json": 1,
                }
                send_sms = requests.get(f"https://sms.ru/sms/send", params=params)
                uid = urlsafe_base64_encode(force_bytes(old_signup.pk))
                ser_instance = serializers.serialize(
                    "json",
                    [
                        old_signup,
                    ],
                )
            elif old_signup and old_signup.is_active == True:
                return JsonResponse({"error": "exist"}, status=400)
            else:
                user.save()
                text = f"Для регистрации на платформе введите код {code}"
                print(urllib.parse.quote_plus(text))
                params = {
                    "api_id": "8A5263F5-F81D-6A7C-B87E-C36C7B10AD93",
                    "to": [phone],
                    "from": "MP LAB",
                    "msg": text,
                    "json": 1,
                }
                send_sms = requests.get(f"https://sms.ru/sms/send", params=params)
                # print(code)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                ser_instance = serializers.serialize(
                    "json",
                    [
                        user,
                    ],
                )

            return JsonResponse({"instance": ser_instance}, status=200)
        else:
            msg = "Форма заполнена не верно"
            error = list(form.errors.keys())[0]
            print(form.errors)
            return JsonResponse({"error": error}, status=400)
    return render(request, "accounts/register.html", {"form": form})


@csrf_exempt
def register_tg_user(request):

    print(1)
    if request.method == "POST":
        data = json.loads(request.body)
        phone = data["phone"]
        if "+" not in phone:
            phone = "+" + phone
        tg_id = data["tg_id"]
        tariff = data["tariff"]
        raw_password = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )
        hash_password = make_password(raw_password)

        user = authenticate(phone=phone, password=raw_password)

        if User.objects.filter(phone=phone).exists():
            old_signup = User.objects.get(phone=phone)
        else:
            old_signup = False

        # if old_signup and old_signup.is_active == False:
        #     uid = urlsafe_base64_encode(force_bytes(old_signup.pk))
        if old_signup and old_signup.is_active == True:
            return JsonResponse({"result": "exist"}, status=200)
        else:
            if old_signup and old_signup.is_active == False:
                user = old_signup
            else:
                user = User.objects.create(phone=phone, password=hash_password)
            tg_api_token = token_hex(16)
            obj = ClientSettings.objects.update_or_create(
                {"tg_chat_id": tg_id, "tg_token": tg_api_token, "client_id": user.id},
                client_id=user.id,
            )

            try:
                pass
                # r = requests.post(
                #     "https://app.mplab.io/amotest/",
                #     json={"client_id": user.id, "type_deal": "register"},
                # )
            except:
                pass

            if tariff is not None:

                tariff = UnicTariff.objects.get(title=tariff)
                start_date = date.today()
                end_date = date.today() + timedelta(days=tariff.days)

                if tariff.end_date > start_date:

                    o = Order.objects.create(
                        client_id=user.id,
                        tariff=tariff.title,
                        period_months=1,
                        paid_status=True,
                    )
                    p = Paid.objects.create(
                        client_id=user.id,
                        start_date=start_date,
                        end_date=end_date,
                        order_id=o.id,
                    )
                    l = Limits.objects.create(
                        client_id=user.id,
                        paid_info_id=p.id,
                        order_id=o.id,
                        start_date=start_date,
                        end_date=end_date,
                        buyout_limit=tariff.buyout_limit,
                        review_limit=tariff.review_limit,
                        like_limit=tariff.like_limit,
                        like_review_limit=tariff.like_review_limit,
                        question_limit=tariff.question_limit,
                    )
                    # obj = ClientSettings.objects.create(
                    #     client_id=user.id,
                    #     tg_chat_id=tg_id,
                    #     tg_token=tg_api_token,
                    #     unictariff_id=tariff.id,
                    # )

                    # else:
                    return JsonResponse(
                        {
                            "result": raw_password,
                            "tariff": {
                                "days": tariff.days,
                                "buyout_limit": tariff.buyout_limit,
                                "review_limit": tariff.review_limit,
                                "like_limit": tariff.like_limit,
                                "question_limit": tariff.question_limit,
                                "like_review_limit": tariff.like_review_limit,
                            },
                        },
                        status=200,
                    )
            return JsonResponse(
                {
                    "result": raw_password,
                },
                status=200,
            )


@csrf_exempt
def reset_tg_password(request):
    if request.method == "POST":
        data = json.loads(request.body)
        tg_chat_id = data["tg_id"]
        user = ClientSettings.objects.get(tg_chat_id=tg_chat_id)
        # user = User.objects.get(id=user.client_id)

        raw_password = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )
        hash_password = make_password(raw_password)

        User.objects.filter(id=user.client_id).update(password=hash_password)
        # User.objects.get(id=user.client_id)
        return JsonResponse({"result": raw_password}, status=200)

        # return JsonResponse({1: 1}, status=400)


@csrf_exempt
def activate(request, code):
    print(request.POST["phone"])
    phone = (
        request.POST["phone"]
        .replace("(", "")
        .replace(")", "")
        .replace("-", "")
        .replace(" ", "")
    )
    referrer = request.POST["referrer"]
    print(referrer)
    if phone.startswith("8"):
        phone = "+7" + phone[1:]
    elif phone.startswith("9"):
        phone = "+7" + phone
    elif not phone.startswith("+"):
        phone = "+" + phone
    user = User.objects.get(phone=phone)
    if is_ajax(request=request) and request.method == "POST":
        if code == force_text(urlsafe_base64_decode(user.code)):
            user.is_active = True
            tg_api_token = token_hex(16)
            new_api_token = ClientSettings.objects.update_or_create(
                {"tg_token": tg_api_token, "client_id": user.id}, client_id=user.id
            )

            user.save()
            try:
                r = requests.post(
                    "https://app.mplab.io/amotest/",
                    json={"client_id": user.id, "type_deal": "register"},
                )
            except:
                pass

            if referrer:
                referrer_object = ReferralLinks.objects.get(code=referrer)
                ReferralUsers.objects.create(source=referrer_object, user=user)
            return JsonResponse({1: 1}, status=200)
    return JsonResponse({1: 1}, status=400)


def send_sms_again(request):
    print(request.GET.get("phone"))
    phone = request.GET.get("phone")
    phone = phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
    if phone.startswith("8"):
        phone = "+7" + phone[1:]
    elif phone.startswith("9"):
        phone = "+7" + phone
    elif not phone.startswith("+"):
        phone = "+" + phone
    user = User.objects.get(phone=phone)
    code = "".join(["{}".format(random.randint(0, 9)) for num in range(0, 6)])
    user.code = urlsafe_base64_encode(force_bytes(code))
    user.last_sms_date = datetime.datetime.now(datetime.timezone.utc)
    user.save()
    text = f"Для регистрации на платформе введите код {code}"
    print(urllib.parse.quote_plus(text))
    params = {
        "api_id": "8A5263F5-F81D-6A7C-B87E-C36C7B10AD93",
        "to": [phone],
        "from": "MP LAB",
        "msg": text,
        "json": 1,
    }
    send_sms = requests.get(f"https://sms.ru/sms/send", params=params)
    print(code)
    ser_instance = serializers.serialize(
        "json",
        [
            user,
        ],
    )
    return JsonResponse({"instance": ser_instance}, status=200)


def send_sms_reset(request):
    print(request.GET.get("phone"))
    phone = request.GET.get("phone")
    phone = phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
    if phone.startswith("8"):
        phone = "+7" + phone[1:]
    elif phone.startswith("9"):
        phone = "+7" + phone
    elif not phone.startswith("+"):
        phone = "+" + phone
    try:
        user = User.objects.get(phone=phone)
    except:
        return JsonResponse({"instance": "not exist phone"}, status=400)
    code = "".join(["{}".format(random.randint(0, 9)) for num in range(0, 6)])
    user.code = urlsafe_base64_encode(force_bytes(code))
    user.last_sms_date = datetime.datetime.now(datetime.timezone.utc)
    user.save()
    text = f"Для восстановления доступа на платформе введите код {code}"
    print(urllib.parse.quote_plus(text))
    params = {
        "api_id": "8A5263F5-F81D-6A7C-B87E-C36C7B10AD93",
        "to": [phone],
        "from": "MP LAB",
        "msg": text,
        "json": 1,
    }
    send_sms = requests.get(f"https://sms.ru/sms/send", params=params)
    print(code)
    ser_instance = serializers.serialize(
        "json",
        [
            user,
        ],
    )
    return JsonResponse({"instance": ser_instance}, status=200)


@csrf_exempt
def reset_password(request, code):
    print(request.POST["phone"])
    phone = (
        request.POST["phone"]
        .replace("(", "")
        .replace(")", "")
        .replace("-", "")
        .replace(" ", "")
    )
    if phone.startswith("8"):
        phone = "+7" + phone[1:]
    elif phone.startswith("9"):
        phone = "+7" + phone
    elif not phone.startswith("+"):
        phone = "+" + phone
    user = User.objects.get(phone=phone)
    if is_ajax(request=request) and request.method == "POST":
        if code == force_text(urlsafe_base64_decode(user.code)):
            return JsonResponse({1: 1}, status=200)
    return JsonResponse({1: 1}, status=400)


def reset_password_done(request):
    if request.method == "POST":
        print(request.POST)
        password1 = request.POST["password1"]
        password2 = request.POST["password2"]
        if password1 != password2:
            return JsonResponse({"resp": "bad"}, status=400)
        else:
            phone = (
                request.POST["phone"]
                .replace("(", "")
                .replace(")", "")
                .replace("-", "")
                .replace(" ", "")
            )
            if phone.startswith("8"):
                phone = "+7" + phone[1:]
            elif phone.startswith("9"):
                phone = "+7" + phone
            elif not phone.startswith("+"):
                phone = "+" + phone
            user = User.objects.get(phone=phone)
            user.set_password(password1)
            user.save()
            return JsonResponse({"resp": "ok"}, status=200)
