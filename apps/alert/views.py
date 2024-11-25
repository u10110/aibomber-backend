import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from email import header
from xml.parsers.expat import ExpatError

import pytest
import requests
import xmltodict
from decouple import config
from django.contrib.auth.decorators import login_required
from django.db.models import Q

# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from loguru import logger
from numpy import product
# from pkg_resources import ResolutionError
from selenium import webdriver
from selenium.webdriver.common.by import By

from apps.billing.models import Bank, Paid
from apps.home.services.proxy import get_proxy

# from ..home.helper import Helper
from ..home.models import (
    AmoCrm,
    ClientSettings,
)
from .conftest import ResultsCollector, get_response_from_test
from .models import NotificationMessage, NotificationRead, TgMessage


TELEGRAM_CHAT_ID_DEV = config("TELEGRAM_CHAT_ID_DEV")
TELEGRAM_TOKEN_DEV = config("TELEGRAM_TOKEN_DEV")

TELEGRAM_CHAT_ID = config("TELEGRAM_CHAT_ID")
TELEGRAM_TOKEN = config("TELEGRAM_TOKEN")

SELENOID_URL = config("SELENOID_URL")





def read_notifications(request):
    date_now = datetime.now(timezone.utc)
    notifications_readed = NotificationRead.objects.filter(
        client=request.user
    ).values_list("message", flat=True)
    notifications = NotificationMessage.objects.filter(is_active=True).filter(
        Q(active_until__gte=date_now) | Q(active_until=None)
    )
    for notification in notifications:
        if notification.id not in notifications_readed:
            NotificationRead.objects.create(client=request.user, message=notification)
    return JsonResponse({"resp": "ok"})


def send_to_telegram(data, notify=False):
    try:
        trigger = data["notification"]["@trigger"]
        status = data["notification"]["@status"]
        user = data["notification"]["executions"]["execution"]["user"].replace(
            "_", "\_"
        )
        spider = data["notification"]["executions"]["execution"]["job"]["name"]
        job_link = data["notification"]["executions"]["execution"]["job"]["@permalink"]
        # print(trigger, status, user, spider, job_link)
        if notify:
            text = f"`[{trigger}] `[{spider}]({job_link})` {status} (owner: `@erreramersedes`)`"
        else:
            text = f"`[{trigger}] `[{spider}]({job_link})` {status}`"
        requests.post(
            url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN_DEV}/sendMessage",
            data=dict(chat_id=TELEGRAM_CHAT_ID_DEV, text=text, parse_mode="Markdown"),
        )
    except KeyError as key:
        pass
    #     app.logger.error('Invalid webhook structure. Failed to fetch: %s', key)
    # except RequestException as error:
    #     app.logger.error('Failed to request Telegram: %s', error)


def send_to_telegram_client(data, notify=False):
    try:
        # trigger = data['notification']['@trigger']
        status = data["notification"]["@status"]
        user = data["notification"]["executions"]["execution"]["user"].replace(
            "_", "\_"
        )
        spider = data["notification"]["executions"]["execution"]["job"]["name"]
        message = data["notification"]["executions"]["execution"]["job"]["message"]
        # job_link = data['notification']['executions']['execution']['job']['@permalink']

        related = ClientSettings.objects.filter(client_id=user)
        for object in related:
            tg_chat_id = object.tg_chat_id

        # print(trigger, status, user, spider, job_link)
        if notify:
            text = f"`[{status}] [{spider}]` {message}"
        else:
            text = f"`[{status}] [{spider}]` {message}"

        requests.post(
            url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data=dict(chat_id=tg_chat_id, text=text, parse_mode="Markdown"),
        )
    except KeyError as key:
        pass


def handle(request, status):
    if request.method == "POST":
        try:
            data = xmltodict.parse(request.body)
            print(data)
        except ExpatError:
            pass
            # app.logger.error('Failed to parse XML content.')
        else:
            notify = "failure" in status
            send_to_telegram(data, notify=notify)
        return JsonResponse({"respond": "ok"}, status=200)


def handle_user(request, status):
    if request.method == "POST":

        try:
            data = xmltodict.parse(request.body)
            client_id = data["notification"]["executions"]["execution"]["user"].replace(
                "_", "\_"
            )
            like_count = ClientSettings.objects.filter(client_id=client_id)
            print(data)
        except ExpatError:
            pass
            # app.logger.error('Failed to parse XML content.')
        else:
            notify = "failure" in status
            send_to_telegram_client(data, notify=notify)
        return JsonResponse({"respond": "ok"}, status=200)


def handle_user_sms(request):
    if request.method == "POST":
        data = json.loads(request.body)
        client_id = data["client_id"]
        product_title = data["product"]["title"]
        product_price = data["product"]["price"]
        tg_chat_id = ClientSettings.objects.filter(client_id=client_id)[0].tg_chat_id
        if tg_chat_id:
            # tg_chat_id=tg_chat_id[0].tg_chat_id
            text = f"Мы заменяем способ оплаты через Telegram с ручным вводом кода из смс на Telegram СБП Уведомления об оплатах и подтверждении оплат будут приходить в @mplabio\_bot \n\r\n\r Этот телеграм бот и способ оплаты будет закрыт в скором времени \n\r\n\r Для оплаты товара `{product_title}` по цене `{product_price}` введите код из смс:"
            requests.post(
                url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data=dict(chat_id=tg_chat_id, text=text, parse_mode="Markdown"),
            )
            deltaa = datetime.now() + timedelta(seconds=2)
            present = datetime.now()
            for i in range(30):
                # try:
                object = (
                    TgMessage.objects.filter(tg_chat_id=tg_chat_id)
                    .all()
                    .order_by("-id")[:1]
                )
                if object:
                    object = object[0]
                    if datetime.strptime(object.date, "%Y-%m-%d %H:%M:%S") > deltaa:
                        time_message = object.date
                        message = object.text
                        pattern = re.compile("^\d{4,6}$")
                        if pattern.match(message):
                            requests.post(
                                url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                                data=dict(
                                    chat_id=tg_chat_id,
                                    text="Код успешно получен",
                                    parse_mode="Markdown",
                                ),
                            )
                            return JsonResponse({"respond": message}, status=200)
                time.sleep(10)
        else:
            return JsonResponse({"respond": "Client have not tg_id"}, status=200)


def billing_check(request):
    if request.method == "POST":
        data = json.loads(request.body)
        if "tg_id" in data:
            tg_id = data["tg_id"]
            client_settings = ClientSettings.objects.filter(tg_chat_id=tg_id).first()
        elif "id" in data:
            id = data["id"]
            client_settings = ClientSettings.objects.filter(client_id=id).first()
        if client_settings:
            if not Paid.objects.filter(client_id=client_settings.client_id).exists():
                return JsonResponse({"result": False})
            paid = Paid.objects.filter(client_id=client_settings.client_id).latest("id")
            now = date.today()
            if paid and paid.end_date > now:
                status = True
            else:
                status = False
            return JsonResponse({"result": status})
        else:
            return JsonResponse({"result": False})


def refresh_tg_amo(request):
    if request.method == "POST":
        data = json.loads(request.body)
        params = {
            "client_id": "c2ee80a7-cfbd-4d6a-b8a4-9f1b61514bbb",
            "client_secret": "hypFpnGHcX9b3QWaPdoQlOEH55l4Zlxvk1xHMJiooqU0OZ2Dr9w7oY8iehk0yBEX",
            "grant_type": "authorization_code",
            "code": data["code"],
            "redirect_uri": "https://app.mplab.io/",
        }

        url = "https://mplabio.amocrm.ru/oauth2/access_token"
        r = requests.post(url, data=params)
        print(r.json())
        if "access_token" not in r.json():
            return JsonResponse(r.json())
        try:
            amo = AmoCrm.objects.get(id=1)
            amo.tg = r.json()
            amo.save()
        except:
            AmoCrm(tg=r.json(), website={}).save()
        return JsonResponse({"result": True})


def refresh_website_amo(request):
    if request.method == "POST":
        data = json.loads(request.body)
        params = {
            "client_id": "a35f023e-33ed-4d03-b951-1b14eef49a1e",
            "client_secret": "2Uh5f7oThcQ8AtOYCc4NU2KxJo0qqBp6Zq0q65C8tOUHuoOYaJTP5DDmZCD6H6WJ",
            "grant_type": "authorization_code",
            "code": data["code"],
            "redirect_uri": "https://app.mplab.io/",
        }

        url = "https://mplabio.amocrm.ru/oauth2/access_token"
        r = requests.post(url, data=params)
        if "access_token" not in r.json():
            return JsonResponse(r.json())
        print(r.json())
        try:
            amo = AmoCrm.objects.get(id=1)
            amo.website = r.json()
            amo.save()
        except:
            AmoCrm(tg={}, website=r.json()).save()

        return JsonResponse({"result": True})


def check_amo_tokens(request):
    if request.method == "POST":
        amo = AmoCrm.objects.get(id=1)
        response = {}
        data = {
            "client_id": "a35f023e-33ed-4d03-b951-1b14eef49a1e",
            "client_secret": "2Uh5f7oThcQ8AtOYCc4NU2KxJo0qqBp6Zq0q65C8tOUHuoOYaJTP5DDmZCD6H6WJ",
            "grant_type": "refresh_token",
            "refresh_token": amo.website["refresh_token"],
            "redirect_uri": "https://app.mplab.io/",
        }

        url = "https://mplabio.amocrm.ru/oauth2/access_token"
        r = requests.post(url, data=data)
        if "access_token" not in r.json():
            response["website"] = "invalid, need refresh"
        else:
            response["website"] = "OK"
            amo.website = r.json()
            amo.save()

        data = {
            "client_id": "c2ee80a7-cfbd-4d6a-b8a4-9f1b61514bbb",
            "client_secret": "hypFpnGHcX9b3QWaPdoQlOEH55l4Zlxvk1xHMJiooqU0OZ2Dr9w7oY8iehk0yBEX",
            "grant_type": "refresh_token",
            "refresh_token": amo.tg["refresh_token"],
            "redirect_uri": "https://app.mplab.io/",
        }
        r = requests.post(url, data=data)
        if "access_token" not in r.json():
            response["tg"] = "invalid, need refresh"
        else:
            response["tg"] = "OK"
            amo.tg = r.json()
            amo.save()

        return JsonResponse(response)

