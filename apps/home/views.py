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

from apps.alert.views import billing_check, get_pvz
from apps.authentication.models import UserInfo
from apps.billing.helper import Helper as BHelper
from apps.billing.models import Limits, Order, Paid, UnicTariff
from apps.users_control.models import ReferalCounter, UsersAgreement
from apps.wb_data.models import Client_tokens
from apps.wb_data.views import *
from core.settings import MEDIA_ROOT

from .forms import *
from .helper import Helper
from .models import (
    DBS,
    AddingReview,
    BoostLike,
    BoostLikeReview,
    BoostQuestion,
    ClientCard,
    ClientProduct,
    ClientPvz,
    ClientSettings,
    Marketplace,
    ProductBuyout,
    Pvz,
    TochkaNumbers,
)
from .module import *
from .services.search_promotion import *
from .services.services import MinioService
from .WB_token import X64ApiClient


def error(request):
    return render(request, "errors/technical_break.html")

def dynamic_page(request,page_name):
    return render(request, f'home/{page_name}.html')


def good_feedbacks(request):
    return render(request, "apps/good_feedbacks.html")


def question_delete(request, pk):
    item = BoostQuestion.objects.get(id=pk, client=request.user.id)
    item.delete()
    return HttpResponseRedirect("/questions?status=active")


def generate_text_review(request):
    if request.method == "POST":
        data = request.POST
        url = "https://qd625qqhr1.execute-api.us-east-2.amazonaws.com/api/product_card/create"
        params = {
            "subject": data["desc"],
            "keywords": data["keywords"].replace(",", ", "),
            "code": "product-user-review",
            "userKey": "79685101765",
            "apiKey": "8efd771645b0c6f76dd343f87f6ba5fc5497d0521b087f52928c93d74d6b0f5a",
        }
        r = requests.post(url, json=params)
        id = r.json()["data"]["id"]
        url_check = "https://qd625qqhr1.execute-api.us-east-2.amazonaws.com/api/product_card/check"
        params = {
            "id": id,
            "userKey": "79685101765",
            "apiKey": "8efd771645b0c6f76dd343f87f6ba5fc5497d0521b087f52928c93d74d6b0f5a",
        }
        while True:
            r_review_text = requests.post(url_check, json=params)
            resp = r_review_text.json()
            status = resp["data"]["status"]
            if status == "ready":
                review_text = r_review_text.json()["data"]["generatedText"]
                return JsonResponse({"text": review_text}, status=200)
            elif status == "error":
                return JsonResponse({"resp": "bad"}, status=200)
            time.sleep(4)


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


def get_pay_link(request):
    if request.method == "POST":
        buyout_id = request.POST["buyout_id"]
        product_info = ProductBuyout.objects.get(id=buyout_id)
        link = product_info.payment_link
        return JsonResponse({"link": link}, status=200)


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


def get_payment_link(request):
    if request.method == "POST":

        date_now = datetime.datetime.now(datetime.timezone.utc)
        try:
            if Limits.objects.filter(client=request.user).exists():
                limits = Limits.objects.get(
                    client=request.user,
                    start_date__lte=date_now,
                    end_date__gte=date_now,
                )
                limit = limits.buyout_limit

                if limit > 0:

                    data = request.POST
                    product_id = data["product_id"]
                    product_info = ProductBuyout.objects.get(id=product_id)
                    payment_type = data["payment_type"]

                    if (
                        len(
                            ProductBuyout.objects.filter(
                                client_id=product_info.client,
                                status="active",
                                payment_status="pay_await",
                            )
                        )
                        > 3
                    ):
                        is_limit = True
                        link = ""
                    else:
                        params = {
                            "buyout_id": product_info.id,
                            "link_type": "sbp"
                            if request.user_agent.is_mobile and payment_type == "qr"
                            else payment_type,
                            "sex": int(product_info.sex),
                            "sku": int(product_info.product.sku),
                            "AddressId": int(product_info.pvz.status),
                            "Pay_checker": "yes",
                        }
                        host = request.META["HTTP_HOST"]
                        print(f"host is {host}")
                        if host == "app.mplab.io":
                            link = f'https://{request.META["HTTP_HOST"]}/api/wb-buy/'
                        else:
                            link = f'http://{request.META["HTTP_HOST"]}/api/wb-buy/'
                        print(link)
                        r = requests.post(link, data=json.dumps(params))
                        if "resp" in r.json():
                            return JsonResponse(
                                {"resp": "Товара нет в наличии"}, status=400
                            )
                        elif "error" in r.json():
                            return JsonResponse(
                                {"resp": f"{r.json()['error']}"}, status=400
                            )
                        # params = {"buyout_id": 914, "link_type": "qr", "sex": 1, "sku": 50759061, "AddressId": 161076}
                        # r = requests.post(f'http://dev.mplab.io:8080/api/wb-buy/', data=json.dumps(params))
                        link = r.json()["link"]
                        # link = ''
                        product_info = ProductBuyout.objects.get(id=product_id)
                        old_payment_status = product_info.payment_status
                        product_info.payment_status = "pay_await"
                        product_info.pay_method = (
                            "sbp"
                            if request.user_agent.is_mobile and payment_type == "qr"
                            else payment_type
                        )
                        product_info.payment_link = link
                        product_info.pay_link_generated = datetime.datetime.now(
                            datetime.timezone.utc
                        )
                        product_info.save()
                        is_limit = False
                        if (
                            request.user_agent.is_mobile
                            and params["link_type"] == "sbp"
                        ):
                            print(f"asd {link}")
                            return JsonResponse(
                                {
                                    "data": link["data"],
                                    "payment_type": "sbp",
                                    "is_limit": is_limit,
                                },
                                status=200,
                            )
                    return JsonResponse(
                        {
                            "resp": link,
                            "payment_type": payment_type,
                            "is_limit": is_limit,
                        },
                        status=200,
                    )
                else:
                    return JsonResponse(
                        {"resp": "Исчерпан лимит по тарифу"}, status=400
                    )
            else:
                return JsonResponse({"resp": "Необходимо приобрести тариф"}, status=400)
        except Exception as e:
            return JsonResponse({"resp": "Что-то пошло не так"}, status=400)


def check_payed(request):
    if request.method == "POST":
        date_now = datetime.datetime.now(datetime.timezone.utc)
        if Limits.objects.filter(client=request.user).exists():
            limits = Limits.objects.get(
                client=request.user,
                start_date__lte=date_now,
                end_date__gte=date_now,
            )
            limit = limits.buyout_limit

            if limit > 0:
                data = request.POST
                product_id = data["product_id"]
                product_info = ProductBuyout.objects.get(id=product_id)
                product_info.payment_status = "pay_check"
                product_info.save()
                params = {
                    "buyout_id": product_info.id,
                    "sku": int(product_info.product.sku),
                }
                host = request.META["HTTP_HOST"]
                print(f"host is {host}")
                if host == "app.mplab.io":
                    link = f'https://{request.META["HTTP_HOST"]}/api/wb-pay-check/'
                else:
                    link = f'http://{request.META["HTTP_HOST"]}/api/wb-pay-check/'
                print(link)
                r = requests.post(link, data=json.dumps(params))
                limits.buyout_limit -= 1
                limits.save()
                return JsonResponse({"resp": "ok"}, status=200)


def dbs(request):
    context = {}
    if request.method == "POST":
        form = AddDBS(request.POST)
        if form.is_valid():
            data = {
                "marketplace": form.cleaned_data.get("marketplace"),
                "locality_type": form.cleaned_data.get("locality"),
                "locality_name": form.cleaned_data.get("city"),
                "country": form.cleaned_data.get("country"),
                "street": form.cleaned_data.get("street"),
                "building": form.cleaned_data.get("building"),
                "building_k": form.cleaned_data.get("building_k"),
                "building_s": form.cleaned_data.get("building_s"),
                "apartament": form.cleaned_data.get("apartament"),
                "entrance": form.cleaned_data.get("entrance"),
                "intercom": form.cleaned_data.get("intercom"),
                "floor": form.cleaned_data.get("floor"),
                "region": form.cleaned_data.get("region"),
            }
            if data["region"] == "":
                data["region"] = None

            marketplace_id = Helper.marketplace_id(data["marketplace"])

            # make address

            item = data.copy()
            if item["street"]:
                item["street"] = f'улица {item["street"]}, '
            else:
                item["street"] = ""
            if item["building_k"]:
                item["building_k"] = f'к{item["building_k"]}'
            else:
                item["building_k"] = ""
            if item["building_s"]:
                item["building_s"] = f'/{item["building_s"]} '
            else:
                item["building_s"] = ""
            if item["region"]:
                item["region"] = f' {item["region"]}, '
            else:
                item["region"] = ""

            # if item.street and item.building_s and item.building_k and item.apartament:
            address = "{},{} {} {}, {}д. {}{}{}".format(
                item["country"],
                item["region"],
                item["locality_type"],
                item["locality_name"],
                item["street"],
                item["building"],
                item["building_s"],
                item["building_k"],
            )

            DBS.objects.create(
                marketplace_id=marketplace_id,
                client_id=request.user.id,
                apartament=data["apartament"],
                entrance=data["entrance"],
                intercom=data["intercom"],
                floor=data["floor"],
                address=address,
            )
        else:
            print(form.errors)
    related = DBS.objects.filter(client=request.user)
    objects = []
    for item in related:
        if item.apartament:
            item.apartament = f", кв.{item.apartament}"
        else:
            item.apartament = ""

        # if item.street and item.building_s and item.building_k and item.apartament:
        address = "{}{}".format(item.address, item.apartament)
        d_address = {"marketplace": item.marketplace.name, "address": address}
        objects.append(d_address)
    context["objects"] = objects
    form = DBS()
    context["form"] = form
    return render(request, "apps/dbs.html", context)


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


def questions(request):
    logged_in_user = request.user
    status = request.GET.get("status", "")
    if status == "active":
        related = BoostQuestion.objects.filter(status="active").filter(
            client=logged_in_user
        )
    elif status == "done":
        related = BoostQuestion.objects.filter(status="done").filter(
            client=logged_in_user
        )
    else:
        return HttpResponseRedirect("/questions?status=active")
    context = []
    for item in related:
        if item.product == None:
            data = Helper.check_sku(item.sku, 1)
            if not ClientProduct.objects.filter(
                sku=item.sku, client_id=logged_in_user.id
            ).exists():
                ClientProduct.objects.create(
                    sku=item.sku,
                    title=data["title"],
                    cover=data["cover"],
                    price=data["price"],
                    status="awaiting",
                    client_id=logged_in_user.id,
                    marketplace_id=1,
                )
            new_product = ClientProduct.objects.filter(
                sku=item.sku, client_id=logged_in_user.id
            )[0]
            bq = BoostQuestion.objects.get(id=item.id)
            bq.product = new_product
            bq.save()

    for item in related:
        item.question_date = item.question_date.date()
        item.question_date_seconds = round(time.mktime(item.question_date.timetuple()))
        context.append(item)
    have_questions = False
    have_pricing = False
    if BoostQuestion.objects.filter(client_id=logged_in_user.id).exists():
        have_questions = True
    if Order.objects.filter(client_id=request.user.id, paid_status=True).exists():
        have_pricing = True
    context = {
        "objects": context,
        "haveQuestions": have_questions,
        "havePricing": have_pricing,
    }
    return render(request, "apps/questions.html", context)


def question_create(request):
    logged_in_user = request.user
    context = {}
    if request.method == "POST":
        print("3")
        form = QuestionForm(request.POST)
        if form.is_valid():
            data = {
                "sku": form.cleaned_data.get("sku"),
                "question_text": form.cleaned_data.get("question_text"),
                "question_date": form.cleaned_data.get("question_date"),
                "sex": form.cleaned_data.get("sex"),
            }
            date_now = datetime.datetime.now(datetime.timezone.utc)
            if not Paid.objects.filter(client_id=request.user.id).exists():
                context["error"] = True
                context["error_message"] = "Необходимо приобрести тариф"
            elif (
                Paid.objects.filter(client=request.user).latest("end_date").end_date
                < date_now.date()
            ):
                context["error"] = True
                context["error_message"] = "Необходимо приобрести тариф"
            else:
                try:
                    print("1")
                    if Helper.get_sku_for_question(data["sku"]):
                        product_info = Helper.check_sku(data["sku"], 1)
                        if not ClientProduct.objects.filter(
                            sku=data["sku"], client_id=logged_in_user.id
                        ).exists():
                            ClientProduct.objects.create(
                                sku=data["sku"],
                                title=product_info["title"],
                                cover=product_info["cover"],
                                price=product_info["price"],
                                status="awaiting",
                                client_id=logged_in_user.id,
                                marketplace_id=1,
                            )
                        product = ClientProduct.objects.filter(
                            sku=data["sku"], client_id=logged_in_user.id
                        )[0]

                        question_date = datetime.datetime.combine(
                            data["question_date"],
                            datetime.time(
                                random.randint(8, 23) - 3, random.randint(0, 59)
                            ),
                        )
                        BoostQuestion.objects.create(
                            product=product,
                            client=logged_in_user,
                            sku=data["sku"],
                            question_text=data["question_text"],
                            question_date=question_date,
                            sex=data["sex"],
                        )
                        print("4")
                        context["error"] = False
                        context["error_message"] = "Вопрос добавлен!"
                    else:
                        context["error"] = True
                        context["error_message"] = "SKU не найден"
                except Exception as e:
                    print(e)
                    context["error"] = True
                    context["error_message"] = "SKU не найден"
                    # else:
                    #     context['error'] = True
                    #     context['error_message'] ='Исчерпан лимит по тарифу'
                # else:
                #     context['error'] = True
                #     context['error_message'] ='Исчерпан лимит по тарифу'
        else:
            print(form.errors)
            context["error"] = True
            context["error_message"] = "Неправильно введенные данные"

    else:
        print("2")
        form = QuestionForm()
    context["form"] = form
    print(context)
    return render(request, "apps/question-create.html", context)


@csrf_exempt
def get_size(request):
    if request.method == "POST":
        sizes = Helper.get_sizes(request.POST["sku"])
        if sizes != False:
            return JsonResponse({"sizes": sizes}, status=200)
        else:
            return JsonResponse({"resp": "bad"}, status=400)


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


def group_buyouts(request):
    status = request.GET.get("status", "all")
    related = ProductBuyout.objects.filter(client_id=request.user.id)
    context = {}
    groups = []
    correct_context = {}
    for item in related:
        if item.num_group not in groups:
            groups.append(item.num_group)
            current_group = related.filter(num_group=item.num_group)
            first_element = current_group[0].created_at
            count_all = len(current_group)
            count_done = 0
            count_payed = 0
            context[item.num_group] = {
                "count_all": count_all,
                "products": [],
                "date": first_element,
            }
            old_sku = []
            price_done = 0
            price_all = 0
            for t_item in current_group:
                if t_item.status == "done":
                    count_done += 1
                    count_payed += 1
                elif t_item.status in ["delivery", "ready"]:
                    count_payed += 1
                sku = t_item.product.sku
                image = t_item.product.cover
                title = t_item.product.title
                price_all += t_item.product.price
                if t_item.payment_status == "done":
                    price_done += t_item.product.price
                if sku not in old_sku:
                    context[item.num_group]["products"].append(
                        {"sku": sku, "image": image, "title": title}
                    )
                    old_sku.append(sku)
            context[item.num_group]["count_done"] = count_done
            context[item.num_group]["count_payed"] = count_payed
            context[item.num_group]["price_all"] = price_all
            context[item.num_group]["price_done"] = price_done

            if item.pay_type != "no":
                context[item.num_group]["is_auto_pay"] = True
            else:
                context[item.num_group]["is_auto_pay"] = False

            if count_done == count_all:
                context[item.num_group]["status"] = 0
            else:
                context[item.num_group]["status"] = 1
            if status == "active":
                if context[item.num_group]["status"] == 1:
                    correct_context[item.num_group] = context[item.num_group]
            elif status == "done":
                if context[item.num_group]["status"] == 0:
                    correct_context[item.num_group] = context[item.num_group]
            elif status == "all":
                correct_context[item.num_group] = context[item.num_group]

    new_context = {}
    new_context["data"] = correct_context
    context = new_context
    have_buyout = False
    have_pvz = False
    have_pricing = False
    if ProductBuyout.objects.filter(client_id=request.user.id).exists():
        have_buyout = True
    if ClientPvz.objects.filter(client_id=request.user.id).exists():
        have_pvz = True
    if Order.objects.filter(client_id=request.user.id, paid_status=True).exists():
        have_pricing = True
    context["haveBuyots"] = have_buyout
    context["havePvz"] = have_pvz
    context["havePricing"] = have_pricing

    return render(request, "apps/group_buyouts.html", context)


def sku_to_buyout(request):
    if request.method == "POST":
        dict_default = {
            "count": ["1"],
            "sex": ["50"],
            "size": [""],
            "phrase": [""],
            "date-start": [""],
            "date-end": [""],
            "pvz_selected": [],
        }
        dict_values = {**dict_default, **dict(request.POST)}
        date_now = datetime.datetime.now(datetime.timezone.utc)
        related = (
            ClientPvz.objects.select_related("pvz")
            .select_related("marketplace")
            .filter(client=request.user)
        )
        if len(related) < 1:
            return JsonResponse({"resp": "pvz"}, status=400)
        if not Paid.objects.filter(client_id=request.user.id).exists():
            return JsonResponse({"resp": "tarif"}, status=400)
        elif (
            Paid.objects.filter(client=request.user).latest("end_date").end_date
            < date_now.date()
        ):
            return JsonResponse({"resp": "tarif"}, status=400)
        sku = request.POST["sku"]
        try:
            product = Helper.check_sku(sku, 1)
            if product == False:
                print("stock bad")
                return JsonResponse({"resp": "stock"}, status=400)
        except Exception as e:
            return JsonResponse({"resp": "bad"}, status=400)
        lst_good_pvz = ""
        for item in related:
            productbuyout_bad = ProductBuyout.objects.filter(
                dev_err="bad select pvz", pvz=item.pvz.id
            )
            if len(productbuyout_bad) == 0 and str(item.pvz.id) not in lst_good_pvz:
                lst_good_pvz += str(item.pvz.id) + ","
        count_pvz = len(lst_good_pvz.split(",")) - 1
        sizes = Helper.get_sizes(sku)
        if sizes:
            sizes = [
                f"<option {'selected' if size == dict_values['size'][0] else ''}>{size}</option>\n"
                for size in sizes
            ]
        else:
            sizes = []
        ids = str(int(time.time()))
        response = f"""
            <tr id='tr-{ids}'>
                  <form action="/buyout/create/" method="post" id='{ids}'>
                  <input type="hidden" name="csrfmiddlewaretoken" value="{request.POST['csrfmiddlewaretoken']}">
                    
                    <select id="marketplace-id-{ids}" type="hidden" name="marketplace" class="d-none" name="choices-sizes">
                      <option value="Wildberries" selected="">Wildberries</i></option>
                    </select>
                    <input type="hidden" class='d-none' id='is_dbs-id-{ids}', name='is_dbs' value='False'>
                  <td class='img_product cell'>
                    <img class="ms-1" src="{product['cover']}" alt="hoodie">
                  </td>
                  <td class='sku_product cell'>
                    {sku}
                    <input id="sku-id-{ids}" type="hidden" name="sku" class="multisteps-form__input form-control raz" value='{sku}' />
                  </td>
                  <td class='price_product cell'>{product['price']} ₽</td>
                  <td class='title_product cell'>{product['title']}</td>
                  <td class='count_product cell'>
                      <input value="{dict_values['count'][0]}" oninput="$(this).attr('value', $(this).val())" id="count_item-id-{ids}" type="number" name="count_item" class="w-80 m-0 multisteps-form__input form-control" placeholder="Кол-во"/>
                  </td>
                  <td class='size_product cell'>
                    <div class="form-group mb-0">
                      <select class="form-control w-100" onchange="let selected = $('option:selected', $(this));$('option', $(this)).attr('selected', false);$(selected).attr('selected', true)" id="size-id-{ids}" name="size" style="width:60px;">
                        {sizes}
                      </select>
                    </div>
                  </td>
                  <td class='sex_product cell'>
                    <input  onchange="document.getElementById('rangeValue-{ids}').innerHTML = this.value; document.getElementById('rangeValue_w-{ids}').innerHTML = 100-this.value;$(this).attr('value', $(this).val())" class="col-10 form-range" id="sex-id-{ids}" name="sex" type="range" min="0" max="100" step="10" value="{dict_values['sex'][0]}" >
        
                    <div class="row">
                      <div class="container">
                        <label class="col-6">Женский - <span id="rangeValue_w-{ids}">{100 - int(dict_values['sex'][0])}</span>%</label>
                        <label class="text-end col-5">Мужской - <span id="rangeValue-{ids}">{dict_values['sex'][0]}</span>%</label>
                      </div>
                    </div>
                  </td>
                  <td class='phrase_product cell'>
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                      <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"/>
                    </svg></label>
                    <div class="row position-relative key_phrase-box ml-0">
                      <div class="key-key_phrase col-12">
                        <input value="{dict_values['phrase'][0]}" oninput="$(this).attr('value', $(this).val())" autocomplete="off" id="key_phrase-id-{ids}" type="text" name="key_phrase" class="form-control d-inline-block" placeholder="кожанный кошелек" />
                      </div>
                      
                    </div>
                    <ul class='list-group list-group-horizontal key-list display-inline'>

                    </ul>
                  </td>
                  <td class='date_start_product cell'>
                    <input value="{dict_values['date-start'][0]}" oninput="$(this).attr('value', $(this).val())" autocomplete="off" class="form-control datetimepicker" type="date" placeholder="Укажите дату начала выкупов" id='buyout_date_start-id-{ids}' name="buyout_date_start" data-input>
                  </td>
                  <td class='date_end_product cell'>
                    <input value="{dict_values['date-end'][0]}" oninput="$(this).attr('value', $(this).val())" autocomplete="off" class="form-control datetimepicker" type="date" placeholder="Укажите дату окончания выкупов" id='buyout_date_end-id-{ids}' name="buyout_date_end" data-input>
                  </td>
                  <td class='product_pvz cell'>
                    <button type="button" onclick='pvz_show_product("{ids}");' class="btn-pvz-choice btn btn-primary mt-3" style='background-image: none; background-color: #007bff;'>Выбрать ПВЗ</button>
                <p style="font-size: 0.75rem; display: inline-block;"><label style='font-weight: 1;' id='count_selected_pvz-{ids}'>{count_pvz if not dict_values['pvz_selected'] else len(dict_values['pvz_selected'][0].split(",")) - 1}</label> из {count_pvz}</p>
                <input  type="hidden" class='pvz_selected-{ids}' id="pvz_selected-id-{ids}" name="pvz_selected" value='{lst_good_pvz if not dict_values['pvz_selected'] else dict_values['pvz_selected'][0]}'>
                  </td>
                  <td class='cell'>
                    <a onclick='$("#tr-{ids}").remove();' href='#' style='font-size: 28px; color: #aaaaaa; font-weight: bold;'>
                      <span aria-hidden="true">&times;</span>
                    </a>
                    <a onclick="copyProduct({sku}, '#tr-{ids}', {ids})" id="clip-{ids}" href="#" style="display: inline-block;font-size: 28px;color: #aaaaaa;font-weight: bold;margin-left: 10px;transform: translate(0px, -3px);padding: 5px;">
                      <span aria-hidden="true"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" style="fill: #999;width:15px"><path d="M502.6 70.63l-61.25-61.25C435.4 3.371 427.2 0 418.7 0H255.1c-35.35 0-64 28.66-64 64l.0195 256C192 355.4 220.7 384 256 384h192c35.2 0 64-28.8 64-64V93.25C512 84.77 508.6 76.63 502.6 70.63zM464 320c0 8.836-7.164 16-16 16H255.1c-8.838 0-16-7.164-16-16L239.1 64.13c0-8.836 7.164-16 16-16h128L384 96c0 17.67 14.33 32 32 32h47.1V320zM272 448c0 8.836-7.164 16-16 16H63.1c-8.838 0-16-7.164-16-16L47.98 192.1c0-8.836 7.164-16 16-16H160V128H63.99c-35.35 0-64 28.65-64 64l.0098 256C.002 483.3 28.66 512 64 512h192c35.2 0 64-28.8 64-64v-32h-47.1L272 448z"></path></svg></span>
                    </a>
                  </td>
                  <input type="submit" class='d-none'>
                </form>
                </tr>
        """
        return JsonResponse({"resp": response}, status=200)


def buyout_create(request):
    # print(get_pvz(request).content)
    list_pvz_id = [
        i["properties"]["id"] for i in json.loads(get_pvz(request).content)["features"]
    ]
    logged_in_user = request.user
    context = {}
    is_cloud = ClientSettings.objects.all().filter(client_id=logged_in_user.id)[0]
    if request.method == "POST":
        post_resp = {}
        print(request.POST)

        for i, v in request.POST.items():
            post_resp[i] = v
        print(post_resp)
        form = AddSku(post_resp)
        if form.is_valid():
            data = {
                "marketplace": form.cleaned_data.get("marketplace"),
                "sku": form.cleaned_data.get("sku"),
                "size": form.cleaned_data.get("size"),
                "sex": form.cleaned_data.get("sex"),
                "key_phrase": form.cleaned_data.get("key_phrase"),
                "count_item": form.cleaned_data.get("count_item"),
                "buyout_date_start": form.cleaned_data.get("buyout_date_start"),
                "buyout_date_end": form.cleaned_data.get("buyout_date_end"),
                "is_dbs": form.cleaned_data.get("is_dbs"),
                "pvz_selected": form.cleaned_data.get("pvz_selected"),
                "group_num": form.cleaned_data.get("group_num"),
                "pay_type": form.cleaned_data.get("pay_type"),
                "tg_start_date": form.cleaned_data.get("tg_start_date"),
                "tg_end_date": form.cleaned_data.get("tg_end_date"),
            }
            date_now = datetime.datetime.now(datetime.timezone.utc)
            # if Limits.objects.filter(client=request.user).exists():
            #     limits = Limits.objects.get(client=request.user, start_date__lte=date_now, end_date__gte=date_now)
            #     limit = limits.buyout_limit

            #     if data['count_item'] <= limit:
            # if True:
            marketplace_id = Helper.marketplace_id(data["marketplace"])
            sku = data["sku"]
            # try:
            product = Helper.check_sku(sku, marketplace_id)
            data.update(product)
            print(f"!!!! {data}")
            if not ClientProduct.objects.filter(
                sku=data["sku"], client_id=logged_in_user.id
            ).exists():

                ClientProduct.objects.create(
                    sku=data["sku"],
                    title=data["title"],
                    cover=data["cover"],
                    price=data["price"],
                    status="awaiting",
                    client_id=logged_in_user.id,
                    marketplace_id=marketplace_id,
                    brand_id=data["brand_id"],
                )
            else:
                ClientProduct.objects.filter(
                    sku=data["sku"], client_id=logged_in_user.id
                ).update(price=data["price"])
            new_product = ClientProduct.objects.filter(
                sku=data["sku"], client_id=logged_in_user.id
            )[0]
            print(f"!????????? {new_product}")

            man_probability = data["sex"]
            count_days = (data["buyout_date_end"] - data["buyout_date_start"]).days + 1
            if data["count_item"] - count_days >= 0:
                print(count_days, "----------------")
                date_organize = np.random.multinomial(
                    data["count_item"] - count_days, np.ones(count_days) / count_days
                ) + np.ones(count_days, dtype=int)
                date_organize = sorted(date_organize)
                date_generated = [
                    data["buyout_date_start"] + datetime.timedelta(days=x)
                    for x in range(0, count_days)
                ]
                print(date_generated)
                # if data['key_phrase']:
                #     key_phrase_list = data['key_phrase'][:-1].split(',')
                # else:
                #     key_phrase_list = ['']

                dbs_list = DBS.objects.all()
                # pvz_list = ClientPvz.objects.filter(client=logged_in_user)
                pvz_list = data["pvz_selected"].split(",")[:-1]
                for i in range(0, data["count_item"]):
                    if data["is_dbs"] == "True":
                        dbs_id = random.choice(dbs_list)
                    else:
                        pvz_id = random.choice(pvz_list)
                    key_phrase = data["key_phrase"]
                    sex = random.choices(
                        [0, 1], weights=[100 - man_probability, man_probability]
                    )[0]
                    for date_i in range(count_days):
                        if date_organize[date_i] != 0:
                            buyout_date = date_generated[date_i]
                            if buyout_date == date_now.date() and date_now.hour + 3 > 8:
                                buyout_date = datetime.datetime.combine(
                                    buyout_date,
                                    datetime.time(
                                        random.randint(date_now.hour + 3, 23) - 3,
                                        random.randint(0, 59),
                                    ),
                                )
                            else:
                                buyout_date = datetime.datetime.combine(
                                    buyout_date,
                                    datetime.time(
                                        random.randint(8, 23) - 3, random.randint(0, 59)
                                    ),
                                )
                            date_organize[date_i] -= 1
                            break
                    print("try to create")
                    new_buyout = ProductBuyout.objects.create(
                        pay_type=data["pay_type"],
                        num_group=data["group_num"],
                        is_dbs=data["is_dbs"],
                        sex=sex,
                        size=data["size"],
                        buyout_date=buyout_date,
                        key_phrase=key_phrase,
                        status="active",
                        pvz_id=pvz_id,
                        client_id=logged_in_user.id,
                        marketplace_id=marketplace_id,
                        product_id=new_product.id,
                    )
                    # if data['is_dbs']=='True':
                    #     new_buyout = ProductBuyout.objects.create(num_group=data['group_num'], is_dbs=data['is_dbs'], sex=sex, size=data['size'], buyout_date=buyout_date, key_phrase=key_phrase, status="active", dbs_address=dbs_id, client_id=logged_in_user.id, marketplace_id=marketplace_id, product_id=new_product[0].id)
                    # else:
                    #     new_buyout = ProductBuyout.objects.create(num_group=data['group_num'], is_dbs=data['is_dbs'], sex=sex, size=data['size'], buyout_date=buyout_date, key_phrase=key_phrase, status="active", pvz_id=pvz_id, client_id=logged_in_user.id, marketplace_id=marketplace_id, product_id=new_product[0].id)

                print(f",,, {new_buyout}")
                context["error"] = False
                context["error_message"] = "Выкупы добавлены!"
                # return render(request, "apps/buyout-create.html", context)
                return JsonResponse({"resp": "ok"}, status=200)

            else:
                context["error"] = True
                context[
                    "error_message"
                ] = "Невозможно добавить данное количество выкупов на выбранное количество дней"
                return JsonResponse(
                    {
                        "error": "Невозможно добавить данное количество выкупов на выбранное количество дней"
                    },
                    status=200,
                )
        else:
            return JsonResponse({"error": "Invalid form"}, status=200)
            # except Exception as e:
            #     print('error', e)
            #     context['error'] = True
            #     context['error_message'] ='Неправильно введенные данные'
            #     messages.info(request, 'Sku не найден, проверьте правильно введенные данные')

        # messages.info(request, 'Форма заполнена не верно!')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = AddSku()
    related = (
        ClientPvz.objects.select_related("pvz")
        .select_related("marketplace")
        .filter(client=logged_in_user)
    )
    lst_good_pvz = []
    for item in related:
        if item.pvz.status in list_pvz_id:
            lst_good_pvz.append([item.pvz.id, item.pvz.address])
        else:
            current_pvz = Pvz.objects.get(id=item.pvz.id)
            current_pvz.actual_status = False
            current_pvz.save()
    lst_good_pvz = [list(x) for x in set(tuple(x) for x in lst_good_pvz)]
    context["count_pvz"] = len(lst_good_pvz)
    context["good_pvz"] = lst_good_pvz
    if "error_message" in context:
        print(context["error_message"])

    cards = ClientCard.objects.filter(client=logged_in_user)
    count_card = len(cards)
    if count_card < 5:
        context["is_more_card"] = "True"
    else:
        context["is_more_card"] = "False"

    return render(request, "apps/buyout-create.html", context)


@csrf_exempt
def get_last_group(request):
    try:
        p = ProductBuyout.objects.filter(client_id=request.user.id).latest("num_group")
        return JsonResponse({"resp": p.num_group})
    except:
        return JsonResponse({"resp": 0})


def buyout_delete(request, pk):
    item = ProductBuyout.objects.get(id=pk)
    response_json = {}
    num_group = len(
        ProductBuyout.objects.filter(num_group=item.num_group, client=request.user)
    )
    if num_group == 1:
        response_json["is_last"] = True
    else:
        response_json["is_last"] = False
    if (
        ProductBuyout.objects.get(id=pk).client_id == request.user.id
        and item.status == "active"
        and item.payment_status != "pay_await"
        and item.payment_status != "pay_check"
    ):
        ProductBuyout.objects.get(id=pk).delete()
    return JsonResponse(response_json)


def export_buyout(request):
    logged_in_user = request.user
    status = request.GET.get("status")
    group = request.GET.get("group")
    file_type = request.GET.get("type")
    if file_type == "csv":
        response = HttpResponse(content_type="text/csv")
        response.write(codecs.BOM_UTF8)
        response["Content-Disposition"] = f'attachment; filename="mplab.csv"'
    elif file_type == "xlsx":
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, options={"remove_timezone": True})
        worksheet = workbook.add_worksheet()
        row_num = 0
    columns = [
        "Продукт",
        "Размер",
        "Статус",
        "Дата",
        "Ключевая фраза",
        "Цена",
        "Цена выкупа",
        "SKU",
        "Номер группы",
    ]
    if file_type == "csv":
        writer = csv.writer(response, delimiter=",")
        writer.writerow(columns)
    elif file_type == "xlsx":
        for col_num in range(len(columns)):
            worksheet.write(row_num, col_num, columns[col_num])

    related = ProductBuyout.objects.filter(client=logged_in_user)
    context = []
    if group != "all":
        related = related.filter(num_group=group)
    for object in related:
        object.buyout_date = object.buyout_date.strftime("%x %X")
        if object.status == "active":
            object.status = "Активный"
        elif object.status == "delivery":
            object.status = "Доставляется"
        elif object.status == "ready":
            object.status = "Готов к получению"
        elif object.status == "done":
            object.status = "Завершено"
        else:
            continue
        context.append(object)
    if file_type == "csv":
        for object in context:
            writer.writerow(
                [
                    object.product.title,
                    object.size,
                    object.status,
                    object.buyout_date,
                    object.key_phrase,
                    object.product.price,
                    object.price_buy,
                    object.product.sku,
                    object.num_group,
                ]
            )
    elif file_type == "xlsx":
        for object in context:
            row_num += 1
            row = [
                object.product.title,
                object.size,
                object.status,
                object.buyout_date,
                object.key_phrase,
                object.product.price,
                object.price_buy,
                object.product.sku,
                object.num_group,
            ]
            for col_num, cell_value in enumerate(row, 0):
                worksheet.write(row_num, col_num, cell_value)
        workbook.close()
        response = HttpResponse(content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = f'attachment; filename="mplab.xlsx"'
        response.write(output.getvalue())
    return response


def buyout(request):
    logged_in_user = request.user
    status = request.GET.get("status", "all")
    group = request.GET.get("group", 1)
    if status == "all":
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(~Q(status="card_add_err"))
            .filter(client=logged_in_user)
        )
    elif status == "active":
        related = (
            ProductBuyout.objects.select_related("product")
            .filter(Q(status="active") | Q(status="error") | Q(status="mp_error"))
            .filter(client=logged_in_user)
        )
    elif status == "delivery":
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(Q(status="delivery") | Q(status="ready"))
            .filter(client=logged_in_user)
        )
    elif status == "done":
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(Q(status="done") | Q(status="return"))
            .filter(client=logged_in_user)
        )
    else:
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(client=logged_in_user)
            .filter(status=status)
        )
        # 'product').select_related('pvz').filter(client=logged_in_user).filter(status="active")
    context = []
    ordered = ["delivery", "ready"]
    related = related.filter(num_group=group)
    if len(related) == 0:
        status = None
        tg_start_date = None
        tg_end_date = None
    else:
        status = related[0].pay_type
        if status == "tg" or status == "tgsbp":
            tg_start_date = related[0].tg_start_date
            tg_end_date = related[0].tg_end_date
            print(tg_start_date, tg_end_date)
        else:
            tg_start_date = "8:00"
            tg_end_date = "23:00"
    cs = ClientSettings.objects.all().filter(client_id=logged_in_user.id)[0]
    is_tg_connect = cs.tg_chat_id
    # is_app_connect = cs.sms_cloud
    size_dict = {}
    for object in related:
        sku = object.product.sku
        sizes = Helper.get_sizes(sku)
        size_dict[sku] = sizes
    context = {
        "objects": related,
        "pay_type": status,
        "is_tg_connect": is_tg_connect,
        "is_auto_pay": True if status != "no" else False,
        "tg_start_date": tg_start_date if tg_start_date else None,
        "tg_end_date": tg_end_date if tg_end_date else None,
        "group": int(group),
        "sizes": size_dict,
    }

    return render(request, "apps/buyout2.html", context)


def export_delivery(request):
    logged_in_user = request.user
    status = request.GET.get("status")
    file_type = request.GET.get("type")
    if file_type == "csv":
        response = HttpResponse(content_type="text/csv")
        response.write(codecs.BOM_UTF8)
        response["Content-Disposition"] = f'attachment; filename="mplab.csv"'
    elif file_type == "xlsx":
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, options={"remove_timezone": True})
        worksheet = workbook.add_worksheet()
        row_num = 0

    if file_type == "csv":
        columns = [
            "Продукт",
            "SKU",
            "Размер",
            "Дата выкупа",
            "Цена",
            "ПВЗ",
            "ФИО",
            "Телефон",
            "Код",
            "Статус",
        ]
        writer = csv.writer(response, delimiter=",")
        writer.writerow(columns)
    elif file_type == "xlsx":
        format = workbook.add_format()
        format.set_pattern(1)
        format.set_bg_color("#EDFFD9")
        columns = [
            "Продукт",
            "SKU",
            "Размер",
            "Цена",
            "Дата выкупа",
            "Статус",
            "QR",
            "ФИО",
            "Телефон",
            "Код",
            "ПВЗ",
            "Дата забора",
            "Код чека",
            "Чек",
        ]
        for col_num in range(len(columns)):
            worksheet.write(row_num, col_num, columns[col_num], format)

    if status == "all":
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(Q(status="delivery") | Q(status="ready") | Q(status="done"))
            .filter(client=logged_in_user)
        )
    else:
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(status=status)
            .filter(client=logged_in_user)
        )
    if file_type == "csv":
        for object in related:
            if object.status == "done":
                status = "Получен"
            elif status == "delivery":
                status = "Доставляется"
            elif object.status == "ready":
                status = (
                    object.delivery_description
                    if object.delivery_description
                    else "Готов к выдаче"
                )
            pvz = (
                object.dev_err
                if object.dev_err and object.status == "Готов к выдаче"
                else object.pvz.address
            )
            writer.writerow(
                [
                    object.product.title,
                    object.product.sku,
                    object.size,
                    object.buyout_date.strftime("%x %X"),
                    object.product.price,
                    object.price_buy,
                    pvz,
                    object.full_name,
                    object.phone,
                    object.code,
                    status,
                ]
            )
    elif file_type == "xlsx":
        rows = related.values_list(
            "product__title",
            "product__sku",
            "size",
            "price_buy",
            "buyout_date",
            "status",
            "qr",
            "full_name",
            "phone",
            "code",
            "pvz__address",
            "dev_err",
            "rId",
            "pay_check",
        )

        worksheet.set_default_row(60)
        worksheet.set_row(0, 20)
        worksheet.set_column(0, 0, 30)
        worksheet.set_column(1, 1, 10)
        worksheet.set_column(2, 2, 7)
        worksheet.set_column(3, 3, 7)
        worksheet.set_column(4, 4, 18)
        worksheet.set_column(5, 5, 18)
        worksheet.set_column(6, 6, 11)
        worksheet.set_column(7, 7, 28)
        worksheet.set_column(8, 8, 12)
        worksheet.set_column(9, 9, 5)
        worksheet.set_column(10, 10, 70)
        worksheet.set_column(11, 11, 18)
        worksheet.set_column(12, 12, 18)
        worksheet.set_column(13, 13, 60)
        for i, row in enumerate(rows):
            row_num += 1
            for col_num in range(len(row)):
                # if col_num == 6:
                #     if row[10] and row[9] == "ready":
                #         print(row[col_num])
                #         pvz = row[11]
                # worksheet.write(row_num, col_num, pvz)
                # else:
                # worksheet.write(row_num, col_num, row[col_num])
                if col_num == 4:
                    date = row[col_num].strftime("%x %X")
                    worksheet.write(row_num, col_num, date)
                elif col_num == 5:
                    if row[col_num] == "done":
                        status = "Получен"
                        cell_format = workbook.add_format()
                        cell_format.set_font_color("black")
                    elif row[col_num] == "delivery":
                        cell_format = workbook.add_format()
                        cell_format.set_bold()
                        cell_format.set_font_color("orange")
                        status = "Доставляется"
                    elif row[col_num] == "ready":
                        cell_format = workbook.add_format()
                        cell_format.set_bold()
                        cell_format.set_font_color("green")
                        status = "Готов к выдаче"
                    worksheet.write(row_num, col_num, status, cell_format)
                elif col_num == 6 and row[col_num]:
                    print(row[col_num])
                    image_data = Helper.get_qr_for_export(row[col_num])
                    print(image_data)
                    worksheet.insert_image(
                        f"G{i + 2}", "url", {"image_data": image_data}
                    )
                elif col_num == 8 and row[col_num]:
                    cell_format = workbook.add_format()
                    cell_format.set_bold()
                    phone = Helper.phone_format(row[col_num])
                    # phone = row[col_num]
                    worksheet.write(row_num, col_num, phone, cell_format)
                elif col_num == 9:
                    cell_format = workbook.add_format()
                    cell_format.set_bold()
                    worksheet.write(row_num, col_num, row[col_num], cell_format)
                    worksheet.write(row_num, col_num, row[col_num])
                elif col_num == 10:
                    cell_format = workbook.add_format()
                    if row[col_num + 1]:
                        worksheet.write(row_num, col_num, row[col_num + 1])
                    else:
                        worksheet.write(row_num, col_num, row[col_num])
                elif col_num == 12:
                    cell_format = workbook.add_format()
                    if row[col_num]:
                        date_end = row[col_num].strftime("%x %X")
                        worksheet.write(row_num, col_num - 1, date_end)
                elif col_num == 13:
                    cell_format = workbook.add_format()
                    if row[col_num]:
                        worksheet.write(row_num, col_num - 1, row[col_num])
                elif col_num == 14:
                    cell_format = workbook.add_format()
                    if row[col_num]:
                        worksheet.write(row_num, col_num - 1, row[col_num])
                elif col_num == 11:
                    pass
                else:
                    worksheet.write(row_num, col_num, row[col_num])
        workbook.close()
        response = HttpResponse(content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = f'attachment; filename="mplab.xlsx"'
        response.write(output.getvalue())
    return response


def delivery(request):
    logged_in_user = request.user
    status = request.GET.get("status", "")
    if status == "all":
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(Q(status="delivery") | Q(status="ready"))
            .filter(client=logged_in_user)
        )
    elif status == "done":
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(Q(status="done") | Q(status="return"))
            .filter(client=logged_in_user)
        )
    else:
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(status=status)
            .filter(client=logged_in_user)
        )
    context = []
    for item in related:
        try:
            phone = item.phone
            if phone != None:
                item.phone = "+7******" + phone[-4:]
        except:
            pass
        context.append(item)
    context = {"objects": context}
    return render(request, "apps/delivery.html", context)


def export_reviews(request):
    logged_in_user = request.user
    status = request.GET.get("status")
    file_type = request.GET.get("type")
    if file_type == "csv":
        response = HttpResponse(content_type="text/csv")
        response.write(codecs.BOM_UTF8)
        response["Content-Disposition"] = f'attachment; filename="mplab.csv"'
    elif file_type == "xlsx":
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, options={"remove_timezone": True})
        worksheet = workbook.add_worksheet()
        row_num = 0
    columns = ["Продукт", "SKU", "Дата выкупа", "Пол"]
    if file_type == "csv":
        writer = csv.writer(response, delimiter=",")
        writer.writerow(columns)
    elif file_type == "xlsx":
        for col_num in range(len(columns)):
            worksheet.write(row_num, col_num, columns[col_num])

    if status == "active":
        exclude = AddingReview.objects.values("buyout_id")
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(status=("done"))
            .filter(client=logged_in_user)
            .exclude(id__in=exclude)
        )
    else:
        related = (
            AddingReview.objects.select_related("buyout")
            .filter(client=logged_in_user)
            .filter(status=status)
        )
    if file_type == "csv":
        for object in related:
            if status == "active":
                if object.sex == "1":
                    sex = "Мужской"
                else:
                    sex = "Женский"
                writer.writerow(
                    [object.product.title, object.product.sku, object.buyout_date, sex]
                )
            else:
                if object.buyout.sex == "1":
                    sex = "Мужской"
                else:
                    sex = "Женский"
                writer.writerow(
                    [
                        object.buyout.product.title,
                        object.buyout.product.sku,
                        object.buyout.buyout_date,
                        sex,
                    ]
                )
    elif file_type == "xlsx":
        for object in related:
            row_num += 1
            if status == "active":
                if object.sex == "1":
                    sex = "Мужской"
                else:
                    sex = "Женский"
                row = [
                    object.product.title,
                    object.product.sku,
                    object.buyout_date,
                    sex,
                ]

            else:
                if object.buyout.sex == "1":
                    sex = "Мужской"
                else:
                    sex = "Женский"
                row = [
                    object.buyout.product.title,
                    object.buyout.product.sku,
                    object.buyout.buyout_date,
                    sex,
                ]
            for col_num, cell_value in enumerate(row, 0):
                worksheet.write(row_num, col_num, cell_value)
        workbook.close()
        response = HttpResponse(content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = f'attachment; filename="mplab.xlsx"'
        response.write(output.getvalue())
    return response


def edit_review(request, review_id):
    review = AddingReview.objects.get(id=review_id)
    images = []
    if request.method != "POST":
        form = AddingReviewForm(instance=review)

        try:
            print(f"{MEDIA_ROOT}/{review.image1.name}")
            images.append(
                {
                    "name": review.image1.name.split("/")[1],
                    "path": f"/media/{review.image1.name}",
                    "size": review.image1.size,
                }
            )
            images.append(
                {
                    "name": review.image2.name.split("/")[1],
                    "path": f"/media/{review.image2.name}",
                    "size": review.image2.size,
                }
            )
            images.append(
                {
                    "name": review.image3.name.split("/")[1],
                    "path": f"/media/{review.image3.name}",
                    "size": review.image3.size,
                }
            )
            images.append(
                {
                    "name": review.image4.name.split("/")[1],
                    "path": f"/media/{review.image4.name}",
                    "size": review.image4.size,
                }
            )
            images.append(
                {
                    "name": review.image5.name.split("/")[1],
                    "path": f"/media/{review.image5.name}",
                    "size": review.image5.size,
                }
            )
        except Exception as e:
            print(e)
        print(images)

    else:
        form = AddingReviewForm(request.POST, request.FILES, instance=review)
        files = request.FILES
        if form.is_valid():
            form.save()
            images_get = {}
            for key, value in dict(request.FILES).items():
                name = value[0].name
                value[0].name = (
                    hashlib.sha256(str.encode(name)).hexdigest()
                    + "."
                    + name.split(".")[-1]
                )
                images_get[key] = value[0]
            count_images = len(dict(request.FILES))
            if count_images > 0:
                images = []
                minio = MinioService()
                if count_images == 1:
                    product = AddingReview.objects.get(id=review_id)
                    product.image1 = images_get["image1"]
                    product.image2 = None
                    product.image3 = None
                    product.image4 = None
                    product.image5 = None
                    product.save()
                    product = AddingReview.objects.get(id=review_id)
                    images.append(product.image1.name)
                elif count_images == 2:
                    product = AddingReview.objects.get(id=review_id)
                    product.image1 = images_get["image1"]
                    product.image2 = images_get["image2"]
                    product.image3 = None
                    product.image4 = None
                    product.image5 = None
                    product.save()
                    images.append(product.image1.name)
                    images.append(product.image2.name)
                elif count_images == 3:
                    product = AddingReview.objects.get(id=review_id)
                    product.image1 = images_get["image1"]
                    product.image2 = images_get["image2"]
                    product.image3 = images_get["image3"]
                    product.image4 = None
                    product.image5 = None
                    product.save()
                    images.append(product.image1.name)
                    images.append(product.image2.name)
                    images.append(product.image3.name)
                elif count_images == 4:
                    product = AddingReview.objects.get(id=review_id)
                    product.image1 = images_get["image1"]
                    product.image2 = images_get["image2"]
                    product.image3 = images_get["image3"]
                    product.image4 = images_get["image4"]
                    product.image5 = None
                    product.save()
                    images.append(product.image1.name)
                    images.append(product.image2.name)
                    images.append(product.image3.name)
                    images.append(product.image4.name)
                elif count_images == 5:
                    product = AddingReview.objects.get(id=review_id)
                    product.image1 = images_get["image1"]
                    product.image2 = images_get["image2"]
                    product.image3 = images_get["image3"]
                    product.image4 = images_get["image4"]
                    product.image5 = images_get["image5"]
                    product.save()
                    images.append(product.image1.name)
                    images.append(product.image2.name)
                    images.append(product.image3.name)
                    images.append(product.image4.name)
                    images.append(product.image5.name)
                for image_path in images:
                    image_name = image_path.split("/")[1]
                    path = f"{MEDIA_ROOT}/{image_path}"
                    minio.put_object(image_name, rf"{path}")
            else:
                AddingReview.objects.filter(id=review_id).update(
                    image1=None, image2=None, image3=None, image4=None, image5=None
                )
            return HttpResponseRedirect(request.path_info)
        else:
            print(form.errors)

    related = ProductBuyout.objects.select_related("product").filter(
        id=review.buyout.id
    )
    context = {"review": review, "form": form, "object": related[0], "images": images}
    return render(request, "apps/reviews-create.html", context)


def reviews(request):
    logged_in_user = request.user
    status = request.GET.get("status", "")
    if status == "active":
        exclude = AddingReview.objects.values("buyout_id")
        related = (
            ProductBuyout.objects.select_related("product")
            .select_related("pvz")
            .filter(status=("done"))
            .filter(client=logged_in_user)
            .exclude(id__in=exclude)
        )
    elif status == "done":
        related = (
            AddingReview.objects.select_related("buyout")
            .filter(client=logged_in_user)
            .filter((Q(status="done") | Q(status="excluded")) | Q(status="error"))
        )
    else:
        related = (
            AddingReview.objects.select_related("buyout")
            .filter(client=logged_in_user)
            .filter(status=status)
        )
    # related = AddingReview.objects.prefetch_related('buyout_set', 'buyout_product_set').filter(client=logged_in_user).filter(status=status)
    # related = AddingReview.objects.prefetch_related('buyout_set', 'buyout_product_set')
    context = []
    for item in related:
        # context.append(item.count_item)
        if status == "active":
            item.buyout_date = item.buyout_date.date()
        else:
            item.buyout.buyout_date = item.buyout.buyout_date.date()

        context.append(item)
        print(item)
    context = {"objects": context}
    return render(request, "apps/reviews.html", context)


def add_review(request, pk):
    # print(pk)
    context = {}
    logged_in_user = request.user
    date_now = datetime.datetime.now(datetime.timezone.utc)
    # if Limits.objects.filter(client=request.user).exists():
    #     limits = Limits.objects.get(client=request.user, start_date__lte=date_now, end_date__gte=date_now)
    #     limit = limits.review_limit
    # else:
    #     limit = None
    # print(limit)

    # if request.method == 'POST' and limit > 0:
    if request.method == "POST":
        form = AddingReviewForm(request.POST, request.FILES)
        files_names = {}
        if form.is_valid():
            if not Paid.objects.filter(client_id=request.user.id).exists():
                return JsonResponse({"resp": "bad"}, status=400)
            elif (
                Paid.objects.filter(client=request.user).latest("end_date").end_date
                < date_now.date()
            ):
                return JsonResponse({"resp": "bad"}, status=400)
            data = {
                "star": form.cleaned_data.get("star"),
                "text": form.cleaned_data.get("text"),
                "review_date": form.cleaned_data.get("review_date"),
            }
            print(request.FILES)
            for key, value in dict(request.FILES).items():
                name = value[0].name
                value[0].name = (
                    hashlib.sha256(str.encode(name)).hexdigest()
                    + "."
                    + name.split(".")[-1]
                )
                data[key] = value[0]
            print(f"!!!! {data}")
            count_images = len(dict(request.FILES))
            if count_images > 0:
                images = []
                minio = MinioService()
                if count_images == 1:
                    new_product = AddingReview.objects.create(
                        review_date=data["review_date"],
                        star=data["star"],
                        text=data["text"],
                        image1=data["image1"],
                        status="plan",
                        client_id=logged_in_user.id,
                        buyout_id=pk,
                    )
                    # images.append(new_product.image1.url)
                    images.append(new_product.image1.name)
                elif count_images == 2:
                    new_product = AddingReview.objects.create(
                        review_date=data["review_date"],
                        star=data["star"],
                        text=data["text"],
                        image1=data["image1"],
                        image2=data["image2"],
                        status="plan",
                        client_id=logged_in_user.id,
                        buyout_id=pk,
                    )
                    images.append(new_product.image1.name)
                    images.append(new_product.image2.name)
                elif count_images == 3:
                    new_product = AddingReview.objects.create(
                        review_date=data["review_date"],
                        star=data["star"],
                        text=data["text"],
                        image1=data["image1"],
                        image2=data["image2"],
                        image3=data["image3"],
                        status="plan",
                        client_id=logged_in_user.id,
                        buyout_id=pk,
                    )
                    images.append(new_product.image1.name)
                    images.append(new_product.image2.name)
                    images.append(new_product.image3.name)
                elif count_images == 4:
                    new_product = AddingReview.objects.create(
                        review_date=data["review_date"],
                        star=data["star"],
                        text=data["text"],
                        image1=data["image1"],
                        image2=data["image2"],
                        image3=data["image3"],
                        image4=data["image4"],
                        status="plan",
                        client_id=logged_in_user.id,
                        buyout_id=pk,
                    )
                    images.append(new_product.image1.name)
                    images.append(new_product.image2.name)
                    images.append(new_product.image3.name)
                    images.append(new_product.image4.name)
                elif count_images == 5:
                    new_product = AddingReview.objects.create(
                        review_date=data["review_date"],
                        star=data["star"],
                        text=data["text"],
                        image1=data["image1"],
                        image2=data["image2"],
                        image3=data["image3"],
                        image4=data["image4"],
                        image5=data["image5"],
                        status="plan",
                        client_id=logged_in_user.id,
                        buyout_id=pk,
                    )
                    images.append(new_product.image1.name)
                    images.append(new_product.image2.name)
                    images.append(new_product.image3.name)
                    images.append(new_product.image4.name)
                    images.append(new_product.image5.name)
                for image_path in images:
                    print(image_path)
                    image_name = image_path.split("/")[1]
                    print(image_name)
                    path = f"{MEDIA_ROOT}/{image_path}"
                    print(path)
                    minio.put_object(image_name, rf"{path}")

            else:
                new_product = AddingReview.objects.create(
                    review_date=data["review_date"],
                    star=data["star"],
                    text=data["text"],
                    status="plan",
                    client_id=logged_in_user.id,
                    buyout_id=pk,
                )
            print("Should to redirect")
            # return HttpResponseRedirect('/reviews?status=active')
            return JsonResponse({"resp": "ok"}, status=200)
        else:
            print(form.errors)
    related = ProductBuyout.objects.select_related("product").filter(id=pk)
    context = {"object": related[0]}
    if not Paid.objects.filter(client_id=request.user.id).exists():
        context["error"] = True
    elif (
        Paid.objects.filter(client=request.user).latest("end_date").end_date
        < date_now.date()
    ):
        context["error"] = True
    else:
        context["error"] = False
    return render(request, "apps/reviews-create.html", context)


def review_delete(request, pk):
    logged_in_user = request.user
    item = AddingReview.objects.filter(id=pk, client=logged_in_user)[0]
    AddingReview.objects.filter(review_date=item.review_date).filter(
        buyout_id=item.buyout_id
    ).filter(Q(status="plan") | Q(status="error")).filter(
        client=logged_in_user
    ).delete()
    date_now = datetime.datetime.now(datetime.timezone.utc)
    return HttpResponseRedirect("/reviews?status=active")


def review_delete_excluded(request, pk):
    logged_in_user = request.user
    item = (AddingReview.objects.get(id=pk, client=logged_in_user),)
    current_item = (
        AddingReview.objects.filter(review_date=item.review_date)
        .filter(buyout_id=item.buyout_id)
        .filter(client=logged_in_user)[0]
    )
    current_item.status = "to_delete"
    current_item.save()
    return HttpResponseRedirect("/reviews?status=active")


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


# //def add_to_favorite(request):
# //    logged_in_user = request.user
# //    if request.method == 'POST':
# //        form = BoostLikeForm(request.POST)
# //        if form.is_valid():
# //            data = {
# //                "marketplace": form.cleaned_data.get('marketplace'),
# //                # "product": form.cleaned_data.get('product'),
# //                "url": form.cleaned_data.get('url'),
# //                "count": form.cleaned_data.get('count'),
# //                # "count_done": form.cleaned_data.get('count_done')
# //                }
# //            marketplace_id = Helper.marketplace_id(data['marketplace'])
# //            # data.update(product)
# //            # new_product = ClientProduct.objects.create(sku=data['url'], title=data['title'], cover=data['cover'], price=data['price'], status="awaiting", client_id=logged_in_user.id, marketplace_id=marketplace_id)
# //            # for i in range(0, data['count']):
# //            print(data)
# //            add_to_favorite = BoostLike.objects.create(status="active", count=data['count'], marketplace_id=marketplace_id, client_id=logged_in_user.id, url=data['url'])
# //    related = BoostLike.objects.select_related('marketplace').filter(client=logged_in_user)
# //    context = []
# //    for item in related:
# //        # context.append(item.count_item)
# //        context.append(item)
# //        print(item)
# //    context = {
# //        'objects': context
# //    }
# //    print(context)
# //    return render(request, "apps/add-to-favorite.html", context)


def add_to_favorite(request):
    logged_in_user = request.user
    context = []
    wrong_link = False
    limit_exceeded = False
    if request.method == "POST":
        logger.debug(f"Form {request.POST}")
        form = BoostLikeForm(request.POST)
        if form.is_valid():
            date_now = datetime.datetime.now(datetime.timezone.utc)
            if not Paid.objects.filter(client_id=request.user.id).exists():
                limit_exceeded = True
            elif (
                Paid.objects.filter(client=request.user).latest("end_date").end_date
                < date_now.date()
            ):
                limit_exceeded = True
            else:
                data = {
                    "marketplace": form.cleaned_data.get("marketplace"),
                    # "product": form.cleaned_data.get('product'),
                    "url": form.cleaned_data.get("url"),
                    "count": form.cleaned_data.get("count"),
                    # "count_done": form.cleaned_data.get('count_done')
                }
                url_type = Helper.is_link_exist(data["url"])
                logger.debug(f"{url_type}")
                if not url_type:
                    wrong_link = True
                else:
                    print(url_type)
                    marketplace_id = Helper.marketplace_id(data["marketplace"])
                    # data.update(product)
                    # new_product = ClientProduct.objects.create(sku=data['url'], title=data['title'], cover=data['cover'], price=data['price'], status="awaiting", client_id=logged_in_user.id, marketplace_id=marketplace_id)
                    # for i in range(0, data['count']):
                    print(data)
                    for i in range(0, data["count"]):
                        add_to_favorite = BoostLike.objects.create(
                            status="active",
                            count=1,
                            marketplace_id=marketplace_id,
                            url_type=url_type,
                            client_id=logged_in_user.id,
                            url=data["url"],
                        )
                    return redirect("add-to-favorite")
                # else:
                #     limit_exceeded = True
                # messages.info(request, f'Превышен допустимый лимит в 2500 лайков/месяц! Добавленно {like_count} лайков')
        else:
            wrong_link = True

            # msg = 'Форма заполнена не верно!'
            # messages.info(request, 'Форма заполнена не верно!')

    related = BoostLike.objects.select_related("marketplace").filter(
        client=logged_in_user
    )
    for item in related:
        # if item.count_done != 1:
        # context.append(item.count_item)
        if context:
            max_count = len(context) - 1
            for i, v in enumerate(context):
                if item.url == v.url:
                    v.count += 1
                    if item.status == "done":
                        v.count_done += 1

                    break
                if i == max_count:
                    item.count = 1
                    if item.status == "done":
                        item.count_done = 1
                    else:
                        item.count_done = 0
                    context.append(item)
                    break
        else:
            if item.status == "done":
                item.count_done = 1
            else:
                item.count_done = 0
            item.count = 1
            context.append(item)
    context = {"objects": context}
    if wrong_link:
        context["error"] = False
        context["error_message"] = "Форма заполнена не верно!"
    if limit_exceeded:
        context["error"] = False
        context["error_message"] = "Необходимо приобрести тариф"
    print(context)
    return render(request, "apps/add-to-favorite.html", context)


def favorite_delete(request, pk):
    logged_in_user = request.user
    item = BoostLike.objects.get(id=pk, client=logged_in_user)
    # print(f"!!!! {item['url']} ")
    print(f"!!!! {item.url} ")
    BoostLike.objects.filter(url=item.url).filter(
        Q(status="active") | Q(status="error")
    ).filter(client=logged_in_user).delete()
    return HttpResponseRedirect("/add-to-favorite/")


def auto_pay_stop(request, group):
    logged_in_user = request.user
    ProductBuyout.objects.filter(client_id=logged_in_user.id).filter(
        num_group=group
    ).update(pay_type="no")
    return HttpResponseRedirect(f"/buyout?status=active&group={group}")


# //def favorite_delete(request, pk):
# //    BoostLike.objects.filter(id=pk).delete()
# //    return HttpResponseRedirect('/add-to-favorite/')


def add_question(request):
    return render(request, "apps/add-question.html")


def add_to_cart(request):
    return render(request, "apps/add-to-cart.html")


def add_to_waiting(request):
    return render(request, "apps/add-to-waiting.html")


@csrf_exempt
def get_likes_data(request):
    if request.method == "POST":
        logged_user = request.user
        data = json.loads(request.POST["data"])
        sku = request.POST["sku"]

        count_all = 0
        for user_id in data.keys():
            if "like" not in data[user_id]:
                data[user_id]["like"] = 0
            if "dislike" not in data[user_id]:
                data[user_id]["dislike"] = 0
            count_all += data[user_id]["like"] + data[user_id]["dislike"]
        if count_all == 0:
            return JsonResponse({"resp": "bad"}, status=400)
        url = f"https://www.wildberries.ru/catalog/{sku}/detail.aspx"
        sku = re.search(r"\d+", sku).group(0)
        product = Helper.check_sku(sku, 1, "review")
        print(product)
        data2 = product
        products = ClientProduct.objects.filter(sku=sku, client=request.user.id)
        if len(products) > 1:
            ClientProduct.objects.filter(sku=sku, client=request.user.id).update(
                title=data2["title"],
                cover=data2["cover"],
                price=data2["price"],
                status="awaiting",
                marketplace_id=1,
                brand_id=data2["brand_id"],
            )
        else:
            product = ClientProduct.objects.update_or_create(
                {
                    "title": data2["title"],
                    "cover": data2["cover"],
                    "price": data2["price"],
                    "status": "awaiting",
                    "client_id": request.user.id,
                    "marketplace_id": 1,
                    "brand_id": data2["brand_id"],
                    "sku": sku,
                },
                sku=sku,
                client_id=request.user.id,
            )
        new_product = ClientProduct.objects.filter(sku=sku, client=request.user.id)
        for user_id in data.keys():
            if "like" not in data[user_id]:
                count_like = 0
            else:
                count_like = data[user_id]["like"]
            if "dislike" not in data[user_id]:
                count_dislike = 0
            else:
                count_dislike = data[user_id]["dislike"]
            print("in")
            count = count_like + count_dislike
            if "info" not in data[user_id]:
                continue
            text = data[user_id]["info"]["text"]
            sender_name = data[user_id]["info"]["name"]
            for task in range(count):
                if count_like > 0:
                    BoostLikeReview.objects.create(
                        product=new_product[0],
                        action="like",
                        text=text,
                        sender_name=sender_name,
                        id_sender=user_id,
                        status="active",
                        url=url,
                        client=logged_user,
                    )
                    count_like -= 1
                elif count_dislike > 0:
                    BoostLikeReview.objects.create(
                        product=new_product[0],
                        action="dislike",
                        text=text,
                        sender_name=sender_name,
                        id_sender=user_id,
                        status="active",
                        url=url,
                        client=logged_user,
                    )
                    count_dislike -= 1

        return JsonResponse({"resp": "ok"}, status=200)


@csrf_exempt
def show_more_review(request):
    if request.method == "POST":
        context = {}
        data = request.POST
        reviews_data = Helper.get_review_data(
            data["sku"], data["count"], order=data["sort"], has_photo=data["has_photo"]
        )
        is_end = "True" if reviews_data[1] == True else "False"
        reviews_data = reviews_data[0]
        if not reviews_data:
            return JsonResponse({"result": "have not new reviews"}, status=200)

        for i in range(len(reviews_data["feedbacks"])):
            date = reviews_data["feedbacks"][i]["createdDate"]
            try:
                date = (
                    datetime.datetime.fromisoformat(date[:-1])
                    .astimezone(timezone.utc)
                    .strftime("%d.%m.%Y %H:%M")
                )
            except:
                date = date[:10]

            reviews_data["feedbacks"][i]["createdDate"] = date
        reviews_html = []
        for review in reviews_data["feedbacks"]:
            print(review)
            print(review["wbUserDetails"])
            photo = (
                f'<img src="https://photos.wbstatic.net/img/{review["wbUserId"]}/small/PersonalPhoto.jpg" class="rounded-circle">'
                if review["wbUserDetails"]["hasPhoto"] == True
                else '<img src="https://images.wbstatic.net/img/0/small/PersonalPhoto.png?2" class="rounded-circle">'
            )
            star1 = "active" if review["productValuation"] > 0 else ""
            star2 = "active" if review["productValuation"] > 1 else ""
            star3 = "active" if review["productValuation"] > 2 else ""
            star4 = "active" if review["productValuation"] > 3 else ""
            star5 = "active" if review["productValuation"] > 4 else ""
            try:
                like = review["votes"]["pluses"]
            except:
                like = 0
            try:
                dislike = review["votes"]["minuses"]
            except:
                dislike = 0
            photos = ""
            if review["photos"] != None:

                for photo_temp in review["photos"]:
                    photo_str = f"""
                        <div class="col-auto">
                            <img src='//feedbackphotos.wbstatic.net/{photo_temp['minSizeUri']}'>
                        </div>
                    
                    """
                    photos += photo_str

            review_html = f"""
                <div class="likes-card col-12 col-lg-6 mt-4" >
                      <div class="card"><div class="row">
                        <div class="col-auto">
                          <div class="profile-photo-container">
                            {photo}
                          </div>
                        </div> 
                        <div class="col">
                          <div class="row">
                            <div class="col-auto name">{review['wbUserDetails']['name']}</div> 
                            <div class="col date">{review['createdDate']}</div>
                          </div> 
                          <div class="row">
                            <div class="review-rating">
                              
                              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" class="{star1}">
                                <path d="M6.87166 4.81324C7.29971 3.74612 7.51373 3.21256 7.86145 3.13861C7.95288 3.11916 8.04738 3.11916 8.13881 3.13861C8.48653 3.21256 8.70055 3.74612 9.1286 4.81324C9.37203 5.4201 9.49374 5.72352 9.72148 5.9299C9.78536 5.98779 9.8547 6.03934 9.92853 6.08384C10.1918 6.24249 10.5204 6.27192 11.1775 6.33078C12.29 6.43041 12.8463 6.48023 13.0162 6.79739C13.0514 6.86308 13.0753 6.9342 13.0869 7.00779C13.1432 7.36315 12.7343 7.73519 11.9165 8.47927L11.6893 8.68589C11.307 9.03376 11.1158 9.2077 11.0052 9.42477C10.9389 9.55498 10.8944 9.69521 10.8736 9.83985C10.8388 10.081 10.8948 10.3333 11.0068 10.838L11.0468 11.0183C11.2476 11.9233 11.348 12.3758 11.2226 12.5982C11.1101 12.798 10.9027 12.9259 10.6736 12.9369C10.4186 12.949 10.0593 12.6562 9.34065 12.0707C8.86718 11.6848 8.63044 11.4919 8.36764 11.4166C8.12747 11.3477 7.87279 11.3477 7.63262 11.4166C7.36982 11.4919 7.13308 11.6848 6.65961 12.0707C5.94096 12.6562 5.58163 12.949 5.32662 12.9369C5.09755 12.9259 4.89019 12.798 4.77761 12.5982C4.65228 12.3758 4.75268 11.9233 4.95348 11.0183L4.99348 10.838C5.10545 10.3333 5.16144 10.081 5.1267 9.83985C5.10585 9.69521 5.06138 9.55498 4.99504 9.42477C4.88446 9.2077 4.69328 9.03376 4.31092 8.68589L4.0838 8.47927C3.26594 7.73519 2.85701 7.36315 2.91333 7.00779C2.92499 6.9342 2.94891 6.86308 2.98409 6.79739C3.15396 6.48023 3.71021 6.43041 4.82272 6.33078C5.47991 6.27192 5.8085 6.24249 6.07173 6.08384C6.14556 6.03934 6.2149 5.98779 6.27878 5.9299C6.50652 5.72352 6.62824 5.4201 6.87166 4.81324Z" stroke="#FF9500" stroke-width="2"></path>
                              </svg>
                              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" class="{star2}">
                                <path d="M6.87166 4.81324C7.29971 3.74612 7.51373 3.21256 7.86145 3.13861C7.95288 3.11916 8.04738 3.11916 8.13881 3.13861C8.48653 3.21256 8.70055 3.74612 9.1286 4.81324C9.37203 5.4201 9.49374 5.72352 9.72148 5.9299C9.78536 5.98779 9.8547 6.03934 9.92853 6.08384C10.1918 6.24249 10.5204 6.27192 11.1775 6.33078C12.29 6.43041 12.8463 6.48023 13.0162 6.79739C13.0514 6.86308 13.0753 6.9342 13.0869 7.00779C13.1432 7.36315 12.7343 7.73519 11.9165 8.47927L11.6893 8.68589C11.307 9.03376 11.1158 9.2077 11.0052 9.42477C10.9389 9.55498 10.8944 9.69521 10.8736 9.83985C10.8388 10.081 10.8948 10.3333 11.0068 10.838L11.0468 11.0183C11.2476 11.9233 11.348 12.3758 11.2226 12.5982C11.1101 12.798 10.9027 12.9259 10.6736 12.9369C10.4186 12.949 10.0593 12.6562 9.34065 12.0707C8.86718 11.6848 8.63044 11.4919 8.36764 11.4166C8.12747 11.3477 7.87279 11.3477 7.63262 11.4166C7.36982 11.4919 7.13308 11.6848 6.65961 12.0707C5.94096 12.6562 5.58163 12.949 5.32662 12.9369C5.09755 12.9259 4.89019 12.798 4.77761 12.5982C4.65228 12.3758 4.75268 11.9233 4.95348 11.0183L4.99348 10.838C5.10545 10.3333 5.16144 10.081 5.1267 9.83985C5.10585 9.69521 5.06138 9.55498 4.99504 9.42477C4.88446 9.2077 4.69328 9.03376 4.31092 8.68589L4.0838 8.47927C3.26594 7.73519 2.85701 7.36315 2.91333 7.00779C2.92499 6.9342 2.94891 6.86308 2.98409 6.79739C3.15396 6.48023 3.71021 6.43041 4.82272 6.33078C5.47991 6.27192 5.8085 6.24249 6.07173 6.08384C6.14556 6.03934 6.2149 5.98779 6.27878 5.9299C6.50652 5.72352 6.62824 5.4201 6.87166 4.81324Z" stroke="#FF9500" stroke-width="2"></path>
                              </svg>
                              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" class="{star3}">
                                <path d="M6.87166 4.81324C7.29971 3.74612 7.51373 3.21256 7.86145 3.13861C7.95288 3.11916 8.04738 3.11916 8.13881 3.13861C8.48653 3.21256 8.70055 3.74612 9.1286 4.81324C9.37203 5.4201 9.49374 5.72352 9.72148 5.9299C9.78536 5.98779 9.8547 6.03934 9.92853 6.08384C10.1918 6.24249 10.5204 6.27192 11.1775 6.33078C12.29 6.43041 12.8463 6.48023 13.0162 6.79739C13.0514 6.86308 13.0753 6.9342 13.0869 7.00779C13.1432 7.36315 12.7343 7.73519 11.9165 8.47927L11.6893 8.68589C11.307 9.03376 11.1158 9.2077 11.0052 9.42477C10.9389 9.55498 10.8944 9.69521 10.8736 9.83985C10.8388 10.081 10.8948 10.3333 11.0068 10.838L11.0468 11.0183C11.2476 11.9233 11.348 12.3758 11.2226 12.5982C11.1101 12.798 10.9027 12.9259 10.6736 12.9369C10.4186 12.949 10.0593 12.6562 9.34065 12.0707C8.86718 11.6848 8.63044 11.4919 8.36764 11.4166C8.12747 11.3477 7.87279 11.3477 7.63262 11.4166C7.36982 11.4919 7.13308 11.6848 6.65961 12.0707C5.94096 12.6562 5.58163 12.949 5.32662 12.9369C5.09755 12.9259 4.89019 12.798 4.77761 12.5982C4.65228 12.3758 4.75268 11.9233 4.95348 11.0183L4.99348 10.838C5.10545 10.3333 5.16144 10.081 5.1267 9.83985C5.10585 9.69521 5.06138 9.55498 4.99504 9.42477C4.88446 9.2077 4.69328 9.03376 4.31092 8.68589L4.0838 8.47927C3.26594 7.73519 2.85701 7.36315 2.91333 7.00779C2.92499 6.9342 2.94891 6.86308 2.98409 6.79739C3.15396 6.48023 3.71021 6.43041 4.82272 6.33078C5.47991 6.27192 5.8085 6.24249 6.07173 6.08384C6.14556 6.03934 6.2149 5.98779 6.27878 5.9299C6.50652 5.72352 6.62824 5.4201 6.87166 4.81324Z" stroke="#FF9500" stroke-width="2"></path>
                              </svg>
                              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" class="{star4}">
                                <path d="M6.87166 4.81324C7.29971 3.74612 7.51373 3.21256 7.86145 3.13861C7.95288 3.11916 8.04738 3.11916 8.13881 3.13861C8.48653 3.21256 8.70055 3.74612 9.1286 4.81324C9.37203 5.4201 9.49374 5.72352 9.72148 5.9299C9.78536 5.98779 9.8547 6.03934 9.92853 6.08384C10.1918 6.24249 10.5204 6.27192 11.1775 6.33078C12.29 6.43041 12.8463 6.48023 13.0162 6.79739C13.0514 6.86308 13.0753 6.9342 13.0869 7.00779C13.1432 7.36315 12.7343 7.73519 11.9165 8.47927L11.6893 8.68589C11.307 9.03376 11.1158 9.2077 11.0052 9.42477C10.9389 9.55498 10.8944 9.69521 10.8736 9.83985C10.8388 10.081 10.8948 10.3333 11.0068 10.838L11.0468 11.0183C11.2476 11.9233 11.348 12.3758 11.2226 12.5982C11.1101 12.798 10.9027 12.9259 10.6736 12.9369C10.4186 12.949 10.0593 12.6562 9.34065 12.0707C8.86718 11.6848 8.63044 11.4919 8.36764 11.4166C8.12747 11.3477 7.87279 11.3477 7.63262 11.4166C7.36982 11.4919 7.13308 11.6848 6.65961 12.0707C5.94096 12.6562 5.58163 12.949 5.32662 12.9369C5.09755 12.9259 4.89019 12.798 4.77761 12.5982C4.65228 12.3758 4.75268 11.9233 4.95348 11.0183L4.99348 10.838C5.10545 10.3333 5.16144 10.081 5.1267 9.83985C5.10585 9.69521 5.06138 9.55498 4.99504 9.42477C4.88446 9.2077 4.69328 9.03376 4.31092 8.68589L4.0838 8.47927C3.26594 7.73519 2.85701 7.36315 2.91333 7.00779C2.92499 6.9342 2.94891 6.86308 2.98409 6.79739C3.15396 6.48023 3.71021 6.43041 4.82272 6.33078C5.47991 6.27192 5.8085 6.24249 6.07173 6.08384C6.14556 6.03934 6.2149 5.98779 6.27878 5.9299C6.50652 5.72352 6.62824 5.4201 6.87166 4.81324Z" stroke="#FF9500" stroke-width="2"></path>
                              </svg>
                              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" class="{star5}">
                                <path d="M6.87166 4.81324C7.29971 3.74612 7.51373 3.21256 7.86145 3.13861C7.95288 3.11916 8.04738 3.11916 8.13881 3.13861C8.48653 3.21256 8.70055 3.74612 9.1286 4.81324C9.37203 5.4201 9.49374 5.72352 9.72148 5.9299C9.78536 5.98779 9.8547 6.03934 9.92853 6.08384C10.1918 6.24249 10.5204 6.27192 11.1775 6.33078C12.29 6.43041 12.8463 6.48023 13.0162 6.79739C13.0514 6.86308 13.0753 6.9342 13.0869 7.00779C13.1432 7.36315 12.7343 7.73519 11.9165 8.47927L11.6893 8.68589C11.307 9.03376 11.1158 9.2077 11.0052 9.42477C10.9389 9.55498 10.8944 9.69521 10.8736 9.83985C10.8388 10.081 10.8948 10.3333 11.0068 10.838L11.0468 11.0183C11.2476 11.9233 11.348 12.3758 11.2226 12.5982C11.1101 12.798 10.9027 12.9259 10.6736 12.9369C10.4186 12.949 10.0593 12.6562 9.34065 12.0707C8.86718 11.6848 8.63044 11.4919 8.36764 11.4166C8.12747 11.3477 7.87279 11.3477 7.63262 11.4166C7.36982 11.4919 7.13308 11.6848 6.65961 12.0707C5.94096 12.6562 5.58163 12.949 5.32662 12.9369C5.09755 12.9259 4.89019 12.798 4.77761 12.5982C4.65228 12.3758 4.75268 11.9233 4.95348 11.0183L4.99348 10.838C5.10545 10.3333 5.16144 10.081 5.1267 9.83985C5.10585 9.69521 5.06138 9.55498 4.99504 9.42477C4.88446 9.2077 4.69328 9.03376 4.31092 8.68589L4.0838 8.47927C3.26594 7.73519 2.85701 7.36315 2.91333 7.00779C2.92499 6.9342 2.94891 6.86308 2.98409 6.79739C3.15396 6.48023 3.71021 6.43041 4.82272 6.33078C5.47991 6.27192 5.8085 6.24249 6.07173 6.08384C6.14556 6.03934 6.2149 5.98779 6.27878 5.9299C6.50652 5.72352 6.62824 5.4201 6.87166 4.81324Z" stroke="#FF9500" stroke-width="2"></path>
                                </svg>
                              </div>
                            </div> 
                            <div class="row review-text">
                                                {review['text']}
                            </div> 
                            <div class="row"></div> 
                            <div class="row appraisals-container">
                              <div class="col-12 likes my-3">
                                  <div class="thumbs thumbs-up d-inline">👍</div> 
                                <p class="appraisals d-inline">Лайков:</p> 
                                <div class="v-counter d-inline justify-content-end">
                                    <input type="button" class="minusBtn " value="-" />
                                    <input user='{review['wbUserId']}' data-name='{review['wbUserDetails']['name']}' data-text='{review['text'][:50] if len(review['text']) > 50 else review['text']}' action='like' type="text" size="25" value="{like}" class="count" /> <span></span>
                                    <input type="button" class="plusBtn" value="+" />
                                </div>
                                </div>
                                  <div class="col-12 dislikes my-3">
                                    <div class="thumbs thumbs-down d-inline">👎</div>
                                    <p class="appraisals d-inline">Дизлайков:</p> 
                                    <div class="v-counter d-inline justify-content-end">
                                      <input type="button" class="minusBtn " value="-" />
                                      <input user='{review['wbUserId']}' data-name='{review['wbUserDetails']['name']}' data-text='{review['text'][:50] if len(review['text']) > 50 else review['text']}' action='dislike' type="text" size="25" value="{dislike}" class="count" /> <span></span>
                                      <input type="button" class="plusBtn" value="+" />
                                    </div>
                                  </div>
                                </div>
                                 <div class="row">
                                  {photos}
                                </div>
                              </div>
                              
                            </div>
                            
                          </div>
                          
                        </div>
            """
            reviews_html.append(review_html)
        context["reviews"] = reviews_html
        context["is_end"] = is_end
        return JsonResponse(context, status=200)


def add_like_to_review(request):
    context = {}
    if request.method == "POST":
        date_now = datetime.datetime.now(datetime.timezone.utc)
        if not Paid.objects.filter(client_id=request.user.id).exists():
            context["error"] = True
            context["error_message"] = "Необходимо приобрести тариф"
        elif (
            Paid.objects.filter(client=request.user).latest("end_date").end_date
            < date_now.date()
        ):
            context["error"] = True
            context["error_message"] = "Необходимо приобрести тариф"
        else:
            sku = request.POST["sku"]
            sort = request.POST["sort"]
            has_photo = request.POST["has_photo"]
            context["sku"] = sku
            context["sort"] = sort
            context["has_photo"] = has_photo
            is_sku = True
            try:
                print(Helper.check_sku(sku, 1))
                is_sku = True
            except Exception as e:
                print(e)
                print("Sku not exist")
                context["error"] = True
                context["error_message"] = "SKU введен неверно"
                is_sku = False
            if is_sku:
                reviews_data = Helper.get_review_data(
                    sku, order=sort, has_photo=has_photo
                )
                if not reviews_data[0] and not reviews_data[1]:
                    context["error"] = True
                    context["error_message"] = "У данного SKU нет отзывов"
                    return render(
                        request, "apps/add-like-to-review.html", context=context
                    )
                context["is_end"] = reviews_data[1]
                reviews_data = reviews_data[0]
                if len(reviews_data["feedbacks"]) != 0:
                    for i in range(len(reviews_data["feedbacks"])):
                        date = reviews_data["feedbacks"][i]["createdDate"]
                        try:
                            date = (
                                datetime.datetime.fromisoformat(date[:-1])
                                .astimezone(timezone.utc)
                                .strftime("%d.%m.%Y %H:%M")
                            )
                        except:
                            date = date[:10]

                        reviews_data["feedbacks"][i]["createdDate"] = date
                    context["reviews"] = reviews_data["feedbacks"]
                else:
                    print("chekkk", reviews_data["feedbacks"])
                    context["error"] = True
                    context["error_message"] = "У данного SKU нет отзывов"
            print(sku)
    elif request.method == "GET":
        print("sdf")
    return render(request, "apps/add-like-to-review.html", context=context)


def like_to_review(request):
    logged_in_user = request.user
    related = BoostLikeReview.objects.filter(client=logged_in_user)
    context = []
    for object in related:
        print(object.text)
        if context:
            max_count = len(context) - 1
            for i, v in enumerate(context):
                # if object.key_phrase == v.key_phrase and object.product.sku == v.product.sku:
                # print(object.buyout_date, v.buyout_date)

                if object.url == v.url and object.id_sender == v.id_sender:
                    # print(v.status)
                    # v.count_item +=1
                    if object.action == "like":
                        try:
                            v.count_like += 1
                        except:
                            v.count_like = 1
                        if object.status == "done":
                            try:
                                v.count_like_done += 1
                            except:
                                v.count_like_done = 1
                    elif object.action == "dislike":
                        try:
                            v.count_dislike += 1
                        except:
                            v.count_dislike = 1
                        if object.status == "done":
                            try:
                                v.count_dislike_done += 1
                            except:
                                v.count_dislike_done = 1

                    break
                if i == max_count:

                    if object.action == "like":
                        object.count_like = 1
                        if object.status == "done":
                            object.count_like_done = 1
                    elif object.action == "dislike":
                        object.count_dislike = 1
                        if object.status == "done":
                            object.count_dislike_done = 1
                    context.append(object)
                    break
        else:
            if object.action == "like":
                object.count_like = 1
                if object.status == "done":
                    object.count_like_done = 1
            else:
                object.count_like = 0
            if object.action == "dislike":
                object.count_dislike = 1
                if object.status == "done":
                    object.count_dislike_done = 1
            else:
                object.count_dislike = 0
            context.append(object)
    context = {"objects": list(reversed(context))}
    return render(request, "apps/like-to-review.html", context)


def index(request):
    print(Helper.get_client_ip(request))
    return HttpResponseRedirect(reverse('projects'))
    # context = {}
    # context["error"] = False
    # if request.method == "POST":
    #     data = request.POST
    #     time = None if data["date_choice"] == "all" else data["date_choice"]
    #     brand = None if data["brand_choice"] == "all" else data["brand_choice"]
    #     api_key = None if data["api_choice"] == "all" else data["api_choice"]
    #     form = Wb_token(request.POST)
    #     if form.is_valid():
    #         wb_token = form.cleaned_data.get("token")
    #         resp_connect = X64ApiClient(wb_token).test()
    #         if resp_connect.status_code == 200:
    #             client_settings = ClientSettings.objects.get(client=request.user)
    #             client_settings.wb_token = wb_token
    #             client_settings.save()
    #     else:
    #         context["error"] = True
    #         context["error_message"] = "Что-то пошло не так"
    # else:
    #     api_key = None
    #     brand = None
    #     time = None
    # client_settings = ClientSettings.objects.get(client=request.user)

    # wb_tokens = Client_tokens.objects.filter(client=request.user).order_by("created_at")
    # if len(wb_tokens) > 0:
    #     for wb_token in wb_tokens:
    #         wb_token = wb_token.token
    #         now = datetime.datetime.now(datetime.timezone.utc)
    #         try:
    #             diff_get_hours = now - wb_token.updated_at
    #         except:
    #             pass
    #         if (
    #             wb_token.updated_at == None
    #             or (diff_get_hours.days * 24 + diff_get_hours.seconds // 3600) >= 1
    #         ):
    #             print("should to update")
    #             update_order_data(request, wb_token.token)

    #     context = get_data_main(request, api_key=api_key, brand=brand, weeks_ago=time)
    # context["wb_tokens"] = wb_tokens
    # return render(request, "apps/main_page.html", context=context)
    # return HttpResponseRedirect(reverse('group-buyouts')+'?status=active')


def pvz(request):
    logged_in_user = request.user
    print(logged_in_user.id)
    wrong_addresses = []
    warning = False
    is_done = False
    context = []
    if request.method == "POST":
        logger.debug(f"Form {request.POST}")
        form = AddPvz(request.POST)
        if form.is_valid():
            address_list = form.cleaned_data.get("address").split("\\n")[:-1]
            count_pvz = len(
                ClientPvz.objects.filter(client_id=logged_in_user.pk)
            ) + len(address_list)
            # return JsonResponse({'resp': 'ok'}, status=599)
            if count_pvz < 5:
                warning = True
            print(
                len(ClientPvz.objects.filter(client_id=logged_in_user.pk))
                + len(address_list)
            )
            print(address_list)
            count_new = 0
            count_old = 0
            for address in address_list:
                address = address.split(";")
                # if re.match(r'(\D+, .+, \d.+\d)', address) is not None:

                data = {
                    "marketplace": form.cleaned_data.get("marketplace"),
                    "address": address[0],
                    "lat": address[1],
                    "lon": address[2],
                    "status": address[3],
                }
                marketplace_id = Helper.marketplace_id("Wildberries")
                if Pvz.objects.filter(
                    status=data["status"],
                    address=data["address"],
                    marketplace_id=marketplace_id,
                ).exists():
                    new_pvz = Pvz.objects.filter(
                        address=data["address"], marketplace_id=marketplace_id
                    )[0]
                else:
                    new_pvz = Pvz.objects.create(
                        address=data["address"],
                        marketplace_id=marketplace_id,
                        status=data["status"],
                        lat=data["lat"],
                        lon=data["lon"],
                    )

                if not ClientPvz.objects.filter(
                    pvz_id=new_pvz.id,
                    marketplace_id=marketplace_id,
                    client_id=logged_in_user.pk,
                ).exists():
                    new_client_pvz = ClientPvz.objects.create(
                        pvz_id=new_pvz.id,
                        marketplace_id=marketplace_id,
                        client_id=logged_in_user.pk,
                    )
                    count_new += 1
                else:
                    count_old += 1
                # else:
                #     wrong_addresses.append(address)
                # return redirect('pvz')
            is_done = True
            form.clean()

        else:
            print(form.errors)
        return JsonResponse(
            {
                "count_all": count_new + count_old,
                "count_new": count_new,
                "count_old": count_old,
            },
            status=200,
        )
    related = (
        ClientPvz.objects.select_related("pvz")
        .select_related("marketplace")
        .filter(client=logged_in_user)
    )
    lst_bad_pvz = []
    lst_good_pvz = []
    for item in related:

        productbuyout_bad = ProductBuyout.objects.filter(
            dev_err="bad select pvz", pvz=item.pvz.id
        )
        productbuyout_good = ProductBuyout.objects.filter(pvz=item.pvz.id).filter(
            ~Q(status="active") & ~Q(status="error")
        )
        if len(productbuyout_bad) != 0:
            lst_bad_pvz.append(item.id)
        elif len(productbuyout_good) != 0:
            lst_good_pvz.append(item.id)
        context.append(item)
    context = {
        "objects": context,
    }
    context["form"] = AddPvz(request.GET)
    print("is_done", is_done)
    if is_done:
        context["is_done"] = True
        context["count_all"] = count_new + count_old
        context["count_new"] = count_new
        context["count_old"] = count_old
    if warning:
        context["warning"] = True
    if len(lst_bad_pvz) != 0:
        context["error_pvz"] = lst_bad_pvz
    if len(lst_good_pvz) != 0:
        context["good_pvz"] = lst_good_pvz
    if len(wrong_addresses) > 0:
        context["error"] = True
        context["addresses"] = wrong_addresses
    else:
        context["error"] = False
    return render(request, "apps/pvz.html", context)


def pvz_delete(request, pk):
    ClientPvz.objects.filter(id=pk, client=request.user.id).delete()
    return HttpResponseRedirect("/pvz/")


def pvz_all_delete(request):
    if request.method == "POST":
        data = request.POST
        print(f"data {data}")
        client_id = data["client_id"]
        print(f"client_idclient_id {client_id}")
        ClientPvz.objects.filter(client=client_id).delete()
    return JsonResponse({"resp": "ok"}, status=200)


def add_card(request):
    context = []
    wrong_card = False
    logged_in_user = request.user
    if request.method == "POST":
        form = AddCardForm(request.POST)
        if form.is_valid():
            data = {
                "number": form.cleaned_data.get("number"),
                "month": form.cleaned_data.get("month"),
                "year": form.cleaned_data.get("year"),
                "cvc": form.cleaned_data.get("cvc"),
            }
            print(data)
            # get_bank_info = requests.get(f'https://lookup.binlist.net/{data["number"]}')
            # bank_info_response = get_bank_info.json()
            # print(bank_info_response)
            # bank = bank_info_response['bank']['name']
            # print(bank)
            new_card = ClientCard.objects.update_or_create(
                number=data["number"],
                month=data["month"],
                year=data["year"],
                cvc=data["cvc"],
                status="active",
                client_id=logged_in_user.id,
            )
        else:
            wrong_card = True
    related = ClientCard.objects.filter(client=logged_in_user).all()
    related_settings = ClientSettings.objects.filter(client=logged_in_user)
    for item in related:
        context.append(item)
        print(item)
    # for item in related_settings:
    #     print(item)
    try:
        tochka_number = related_settings[0].tochka_number
        context = {"objects": context, "tochka_number": tochka_number}
    except:
        context = {
            "objects": context,
        }
    if wrong_card:
        context["error"] = True
        context["error_message"] = "Неверные данные карты"
    else:
        context["error"] = False
    # print(context)
    return render(request, "apps/add-card.html", context)


# def app_download(request):
#     import os
# from django.conf import settings
# from django.http import HttpResponse, Http404

# def download(request, path):
#     file_path = os.path.join(settings.MEDIA_ROOT, path)
#     if os.path.exists(file_path):
#         with open(file_path, 'rb') as fh:
#             response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
#             response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
#             return response
#     raise Http404


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


# def pages(request):
#     print(11)
#     context = {}
#     # All resource paths end in .html.
#     # Pick out the html file name from the url. And load that template.
#     try:

#         load_template = request.path.split('/')[-1]

#         if load_template == 'admin':
#             return HttpResponseRedirect(reverse('admin:index'))

#         segment, active_menu = get_segment(request)

#         context['segment'] = segment
#         context['active_menu'] = active_menu
#         html_template = loader.get_template('home/' + load_template)
#         return HttpResponse(html_template.render(context, request))

#     except template.TemplateDoesNotExist:

#         html_template = loader.get_template('apps/page-404.html')
#         return HttpResponse(html_template.render(context, request))

#     except:
#         html_template = loader.get_template('apps/page-500.html')
#         return HttpResponse(html_template.render(context, request))

# Helper - Extract current page name from request


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


# def all(request):
#     print("asdgasd!!!!!!!!")
#     # одна строка вместо тысячи слов на SQL
#     latest = Buyout.objects.order_by('-sku')[:10]
#     # latest = Buyout.objects.get(id=2)
#     # собираем тексты постов в один, разделяя новой строкой
#     # print(str(latest))
#     context = []
#     for item in latest:
#         context.append(item)
#         print(context)
#     context = {
#         'objects': context
#     }

#     print(context)
#     # return render(request, "index.html", {"posts": latest})
#     return render(request, "apps/buyout.html", context)

# def active(request):
#     print("asdgasd!!!!!!!!")
#     # одна строка вместо тысячи слов на SQL
#     latest = Buyout.objects.get(id=2)
#     # собираем тексты постов в один, разделяя новой строкой
#     # print(str(latest))
#     context = {
#         'objects': contexlatestt
#     }

#     print(context)
#     # return render(request, "index.html", {"posts": latest})
#     return render(request, "apps/buyout.html", context)


def search_promotion(request):
    logged_in_user = request.user
    context = {"objects": []}
    wrong_link = False
    sku_not_found = False
    is_search_promotion = True
    if request.method == "POST":
        context = add_new_search_promotion(request, is_search_promotion, context)
    context = get_search_promotions(request, is_search_promotion, context)

    if wrong_link:
        context["error"] = False
        context["error_message"] = "Артикул не найден!"
    print(context)
    return render(request, "apps/promotion-by-keyword.html", context)


def search_promotion_stop(request, pk):
    logged_in_user = request.user
    ClientPhrase.objects.filter(pk=pk).update(status="stop")
    return HttpResponseRedirect("/search-promotion")


def search_promotion_start(request, pk):
    logged_in_user = request.user
    ClientPhrase.objects.filter(pk=pk).update(status="active")
    return HttpResponseRedirect("/search-promotion")


def position_delete(request, pk):
    logged_in_user = request.user
    object = ClientPhrase.objects.get(pk=pk, client=request.user.id)
    if object.is_search_promotion is False:
        ClientPhrase.objects.get(pk=pk, client=request.user.id).delete()
    else:
        messages.error(
            request,
            "Артикул находится на поисковом продвижении, удаление через поддержку",
        )
    return HttpResponseRedirect("/positions")
    # return render(request, "apps/positions.html", context)


def positions(request):
    logged_in_user = request.user
    context = {"objects": []}
    wrong_link = False
    is_search_promotion = False
    if request.method == "POST":
        context = add_new_search_promotion(request, is_search_promotion, context)
        print(f"context is {context}")
    context = get_search_promotions(request, is_search_promotion, context)

    if wrong_link:
        context["error"] = False
        context["error_message"] = "Артикул не найден!"
    return render(request, "apps/positions.html", context)


def position_details(request, pk):
    if request.method == "POST":
        date_start_raw = request.POST["date_start"]
        date_end_raw = request.POST["date_end"]
        logged_in_user = request.user
        date_end_raw = datetime.datetime.strptime(date_end_raw, "%Y-%m-%d")
        date_start_raw = datetime.datetime.strptime(date_start_raw, "%Y-%m-%d")
        context = {"objects": []}
        context = get_search_promotions(
            request, False, context, pk, date_start_raw, date_end_raw
        )
        context = context["objects"][0].__dict__
        context.pop("_state", None)
        object = json.dumps(context, indent=4, sort_keys=True, default=str)
        object = {"object": object}
        return HttpResponse(
            json.dumps(context, indent=4, sort_keys=True, default=str),
            content_type="application/json",
        )
    else:
        logged_in_user = request.user
        date_start = False
        date_end_raw = datetime.datetime.today() - datetime.timedelta(1)
        date_start_raw = datetime.datetime.today() - datetime.timedelta(29)
        # date_end = datetime.datetime.strftime(date_end, '%Y-%m-%d')
        context = {"objects": []}
        wrong_link = False
        is_search_promotion = False
        context = get_search_promotions(
            request, is_search_promotion, context, pk, date_start_raw, date_end_raw
        )

        if wrong_link:
            context["error"] = False
            context["error_message"] = "Артикул не найден!"
        return render(
            request, "apps/position_details.html", {"object": context["objects"][0]}
        )


def buyout_edit(request):
    if request.method == "POST":
        data = request.POST
        date = data["product_date"].split(".")
        date_buyout = f"{date[2]}-{date[1]}-{date[0]}"
        key_phrase = data["key_phrase"]
        size = data["product_size"] if data["product_size"] != "false" else "0"
        ProductBuyout.objects.filter(client=request.user, id=data["buyout_id"]).update(
            size=size, key_phrase=key_phrase, buyout_date=date_buyout
        )
        return JsonResponse({"resp": "ok"}, status=200)


def buyout_group_delete(request):
    if request.method == "POST":
        data = request.POST
        ProductBuyout.objects.filter(
            client=request.user, num_group=data["index"]
        ).delete()
        return JsonResponse({"resp": "ok"}, status=200)

    
def services(request):
    return render(request, "apps/services.html")




def projects(request):
    return render(request, "apps/projects.html")


def project_create(request):
    return render(request, "apps/project_create.html")

def list_recipient(request):
    return render(request, "apps/list_recipient.html")

def chat(request):
    return render(request, "apps/chat.html")

def channels(request):
    return render(request, "apps/channels.html")
