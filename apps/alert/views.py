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
    AddingReview,
    AmoCrm,
    BoostQuestion,
    ClientSettings,
    Marketplace,
    ProductBuyout,
)
from .conftest import ResultsCollector, get_response_from_test
from .models import NotificationMessage, NotificationRead, TgMessage, ZennoPoster
from .services.services import (
    BuyoutManager,
    Eramp,
    FavoriteManager,
    FavoriteReviewManager,
    QuestionManager,
    ReivewManager,
)
from .services.trash import Position, get_cpm, wb_check_code_runner
from .services.wb_api import WbHepler
from .services.zennolab import ZennoAPI

TELEGRAM_CHAT_ID_DEV = config("TELEGRAM_CHAT_ID_DEV")
TELEGRAM_TOKEN_DEV = config("TELEGRAM_TOKEN_DEV")

TELEGRAM_CHAT_ID = config("TELEGRAM_CHAT_ID")
TELEGRAM_TOKEN = config("TELEGRAM_TOKEN")

SELENOID_URL = config("SELENOID_URL")


# //<notification trigger="trigger" status="status">
# //  <executions>
# //      <execution><user>user</user><job permalink="permalink"><name>spider</name></job></execution>
# //  </executions>
# //</notification>


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


def get_pvz(request):
    pvz_address, pvz_ids = WbHepler.get_pvz_info()
    result_for_map = {"type": "FeatureCollection", "features": []}
    for i in range(0, len(pvz_ids["value"]["pickups"])):
        try:
            rate = pvz_address["value"][str(pvz_ids["value"]["pickups"][i]["id"])][
                "rate"
            ]
        except:
            rate = None
        key_ = str(pvz_ids["value"]["pickups"][i]["id"])
        if key_ not in pvz_address["value"]:
            continue
        result_for_map["features"].append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        pvz_ids["value"]["pickups"][i]["coordinates"][1],
                        pvz_ids["value"]["pickups"][i]["coordinates"][0],
                    ],
                },
                "properties": {
                    "Name": pvz_address["value"][
                        str(pvz_ids["value"]["pickups"][i]["id"])
                    ]["address"],
                    "rate": rate,
                    "id": pvz_ids["value"]["pickups"][i]["id"],
                },
            }
        )

    return JsonResponse(result_for_map, status=200)


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


def sbp_pay(request):
    if request.method == "POST":
        data = json.loads(request.body)
        client_id = data["client_id"]
        product_title = data["product"]["title"]
        product_price = data["product"]["price"]
        sbp_url = data["url"]
        sbp_token = re.findall("(?<=qr\.nspk\.ru/).*?(?=\?)", sbp_url)[0]
        link = f"https://app.mplab.io/api/sbp-page?{sbp_token}"
        client_settings = ClientSettings.objects.filter(client_id=client_id)[0]
        tg_chat_id = client_settings.tg_chat_id
        selected_banks = Bank.objects.filter(clientsettings=client_settings.id).all()
        if tg_chat_id:
            for_buttons = []
            for bank in selected_banks:
                link = f"{sbp_url}{bank.code};end"
                for_buttons.append({"title": bank.name_rus, "url": link})

                # TODO join, forloop for banks and aggregations data
            message = f"Для оплаты товара `{product_title}` по цене `{product_price}` нажмиите на `Оплатить`:"
            sending_data = {
                "tg_id": tg_chat_id,
                "message": message,
                "link": link,
            }
            print(sending_data)
            requests.post(
                url="https://bot.mplab.io/bank_payments",
                json=sending_data,
            )
            return JsonResponse(sending_data, status=200)
        else:
            return JsonResponse({"respond": "Client have not tg_id"}, status=200)


def sbp_page(request):
    from apps.alert.services.sbp import get_sbp_links

    url = request.build_absolute_uri()
    sbp_code = re.findall("(?<=sbp-page\?).*", url)[0]
    print(sbp_code)
    data = get_sbp_links(f"https://qr.nspk.ru/{sbp_code}?")
    return render(request, "apps/spb.html", data)


def eramp(request):
    if request.method == "POST":
        data = json.loads(request.body)
        tg_chat_id = data["tg_chat_id"]
        email = data["email"]
        tariff = data["tariff"]
        tariff_type = data["tariff_type"]
        password = ""
        print(email)
        zenno_api = ZennoAPI()
        such_email = zenno_api.get_current_custome_email(email)
        if "nosuchuser" in such_email:
            print("111111111111111")
            password = zenno_api.register_customer(email).replace("Pass:", "")
        if not password:
            password = "Данная почта ранее была зарегистрирована, пароль у вас"
            print(password)
        print("before func sale_bots")
        response = zenno_api.sale_bots(email, tariff, tariff_type)
        response = xmltodict.parse(response.text)
        sale_id = response["int"]["#text"]
        print(sale_id)
        if sale_id != 0:
            Eramp.add_sale(tg_chat_id, email, sale_id)
            print("before get_custome_box_link")
            print("before func get_custome_box_link")
            link_box = zenno_api.get_custome_box_link(email)

            zenno_api = ZennoAPI()
            sale_id, date_end = Eramp.get_sale(tg_chat_id, email)

            if link_box:
                return JsonResponse(
                    {"email": email, "pass": password, "box_link": link_box}, status=200
                )
            else:
                return JsonResponse(
                    {"status": "get_custome_box_link error"}, status=200
                )
        else:
            return JsonResponse({"status": "sale_id error"}, status=200)


def eramp_change_subscription(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            tg_chat_id = data["tg_chat_id"]
            email = data["email"]
            days = int(data["days"])
            zenno_api = ZennoAPI()

            sale_id, date_end = Eramp.get_sale(tg_chat_id, email)
            zenno_api.change_subscription(tg_chat_id, email, sale_id, days)
            Eramp.update_date_end(tg_chat_id, date_end, days)

            return JsonResponse({"status": "done"}, status=200)
    except Exception as ex:
        raise ValueError(f"{ex}")


def eramp_get_end_date(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            tg_chat_id = data["tg_chat_id"]
            email = data["email"]
            sale_id, date_end = Eramp.get_sale(tg_chat_id, email)
            return JsonResponse({"date_end": date_end}, status=200)
    except Exception as ex:
        raise ValueError(f"{ex}")


def position(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            marketplace_id = data["marketplace_id"]
            tg_chat_id = data["tg_chat_id"]
            sku = data["message"].split(" ", 1)[0]
            print(sku)
            key_phrase = " ".join(data["message"].split(" ", 1)[1::]).strip()
            print(key_phrase)
            p = Position()
            if sku.isdigit() and key_phrase:
                # if p.get_name(sku):
                if Helper.check_sku(sku, marketplace_id):
                    # name = p.get_name(sku)
                    product = Helper.check_sku(sku, marketplace_id)
                    name = product["title"]
                    now = datetime.now()
                    date = str(now.strftime("%d.%m.%Y, %H:%M:%S"))
                    position = p.parse(key_phrase, sku)
                    if position:
                        page = position[0]
                        place = position[1]
                        # position = f'({prs[0]} стр, {prs[1]} место)'
                        return JsonResponse(
                            {
                                "sku": sku,
                                "page": page,
                                "place": place,
                                "key_phrase": key_phrase,
                            },
                            status=200,
                        )
                    else:
                        return JsonResponse(
                            {"error": "Нет товаров по данному артикулу"}, status=200
                        )
                else:
                    return JsonResponse(
                        {"respond": {"error": "Артикул {sku} не найден"}}, status=200
                    )
            else:
                return JsonResponse(
                    {
                        "respond": {
                            "error": "***Неверный формат***\n"
                            + "В запросе должен быть сначала артикул, после чего ключевое слово.\n"
                            + "Пример: `22695156 чехол для iPhone 12`"
                        }
                    },
                    status=200,
                )
        except Exception as ex:
            raise ValueError(f"{ex}")


def advertising_rate(request):
    if request.method == "POST":
        print(request.POST)
        # data = json.loads(request.body)
        data = request.POST
        type_ad = data["type_ad"] if "type_ad" in data else "keyphrase"
        marketplace_id = data["marketplace_id"] if "marketplace_id" in data else 1
        key_phrase = data["key_phrase"]
        cpm_list = get_cpm(key_phrase, type_ad=type_ad)
        return JsonResponse(cpm_list, safe=False)


def wb_buy(request):
    if request.method == "POST":
        # try:
        data = json.loads(request.body)
        logger.info(f"get data request {data}")
        buyout_manager = BuyoutManager(data)
        link = buyout_manager.get_pay_link()
        if not link:
            return JsonResponse({"error": "Что-то пошло не так"})
        elif link == "Not available pvz":
            return JsonResponse({"error": "Нет доступных ПВЗ"})
        elif link == {"resp": "stock"}:
            return JsonResponse({"resp": "stock"})
        return JsonResponse({"link": link})
    # except Exception as es:
    # ProductBuyout.objects.filter(id=data["buyout_id"]).update(
    # payment_status="bad_pay"
    # )
    # logger.error(f"Can not take pay link {es}")


def review_add(request):
    if request.method == "POST":
        # try:
        data = json.loads(request.body)
        review_id = data["id"]
        logger.info(f"get data request {data}")
        review_manager = ReivewManager(review_id)
        response = review_manager.add_review()
        return JsonResponse(response)
    # except Exception as es:
    # AddingReview.objects.filter(id=review_id).update(status="error")
    # logger.error(f"Can not take pay link {es}")


def favorite_add(request):
    if request.method == "POST":
        data = json.loads(request.body)
        favorite_id = data["id"]
        logger.info(f"get data request {data}")
        favorite_manager = FavoriteManager(favorite_id)
        response = favorite_manager.add_favorite()
        return JsonResponse(response)


def question_add(request):
    if request.method == "POST":
        data = json.loads(request.body)
        favorite_id = data["id"]
        logger.info(f"get data request {data}")
        question_manager = QuestionManager(favorite_id)
        response = question_manager.question_add()
        return JsonResponse(response)


def favorite_review_add(request):
    if request.method == "POST":
        data = json.loads(request.body)
        favorite_id = data["id"]
        logger.info(f"get data request {data}")
        favorite_manager = FavoriteReviewManager(favorite_id)
        response = favorite_manager.add_favorite()
        return JsonResponse(response)


def wb_pay_check(request):
    if request.method == "POST":
        data = json.loads(request.body)
        buyout_id = data["buyout_id"]
        nms = data["sku"]
        return JsonResponse({"status": "ok"})


def wb_check_code(request):
    if request.method == "POST":
        data = json.loads(request.body)
        response = wb_check_code_runner(data)
        return JsonResponse(response)


def check_proxy(request):
    proxy = get_proxy()
    logger.debug(f"{proxy}")
    response = requests.get("https://api.ipify.org?format=json", proxies=proxy)
    logger.debug(f"{response}")
    logger.debug(f"{response.text}")
    response = json.loads(response.text)
    return JsonResponse(response)


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


def wb_buy_test(request):
    if request.method == "POST":
        data = json.loads(request.body)
        buyout_id = data["buyout_id"]
        payment = data["payment_type"]
        collector = ResultsCollector()
        result = pytest.main(
            [
                "-x",
                "apps/alert/tests.py",
                f"--buyout_id={buyout_id}",
                f"--payment_type={payment}",
                "-k test_buyout",
            ],
            plugins=[collector],
        )
        response = get_response_from_test(collector, result)
        return JsonResponse(response)


def review_add_test(request):
    if request.method == "POST":
        data = json.loads(request.body)
        review_id = data["review_id"]
        collector = ResultsCollector()
        result = pytest.main(
            ["-x", "apps/alert/tests.py", f"--review_id={review_id}", "-k test_review"],
            plugins=[collector],
        )
        response = get_response_from_test(collector, result)
        return JsonResponse(response)


def favorite_add_test(request):
    if request.method == "POST":
        data = json.loads(request.body)
        favorite_id = data["favorite_id"]
        collector = ResultsCollector()
        result = pytest.main(
            [
                "-x",
                "apps/alert/tests.py",
                f"--favorite_id={favorite_id}",
                "-k test_favorite_add",
            ],
            plugins=[collector],
        )
        response = get_response_from_test(collector, result)
        return JsonResponse(response)


def question_add_test(request):
    if request.method == "POST":
        data = json.loads(request.body)
        favorite_id = data["favorite_id"]
        collector = ResultsCollector()
        result = pytest.main(
            [
                "-x",
                "apps/alert/tests.py",
                f"--favorite_id={favorite_id}",
                "-k test_question",
            ],
            plugins=[collector],
        )
        response = get_response_from_test(collector, result)
        return JsonResponse(response)


def favorite_review_add_test(request):
    if request.method == "POST":
        data = json.loads(request.body)
        favorite_id = data["favorite_id"]
        collector = ResultsCollector()
        result = pytest.main(
            [
                "-x",
                "apps/alert/tests.py",
                f"--favorite_id={favorite_id}",
                "-k test_favorite_review_add",
            ],
            plugins=[collector],
        )
        response = get_response_from_test(collector, result)
        return JsonResponse(response)
