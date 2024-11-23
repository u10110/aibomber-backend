import json
from datetime import datetime, timedelta

import requests
from apps.home.models import Account, ProductBuyout
from apps.home.services.proxy import get_proxy
from apscheduler.schedulers.background import BackgroundScheduler
from decouple import config
from loguru import logger
from numpy import number
from selenium import webdriver
from selenium.webdriver.common.by import By

from . import helper
from .services import BuyoutManager
from .wb_api import WbAPI, WbClientAPI

SELENOID_URL = config("SELENOID_URL")


class Position:
    def __init__(self) -> None:
        pass

    def parse(self, key_phrase, sku):

        off = 0
        page = 0
        # url = (
        # f"https://wbxsearch.wildberries.ru/exactmatch/v2/common?query={key_phrase}"
        # )
        proxy = get_proxy()
        # response = requests.get(url, proxies=proxy)
        # response = json.loads(response.content)
        # shard_key = response["shardKey"]
        # print(shard_key)
        # query = response["query"]
        query = key_phrase
        for page in range(1, 50):
            proxy = get_proxy()
            # url = f"https://wbxcatalog-ru.wildberries.ru/{shard_key}/catalog?spp=0&regions=69,64,86,83,75,4,38,30,33,70,71,22,31,66,68,82,48,1,40,80&stores=117673,122258,122259,125238,125239,125240,6159,507,3158,117501,120602,120762,6158,121709,124731,159402,2737,130744,117986,1733,686,132043&pricemarginCoeff=1.0&reg=0&appType=1&offlineBonus=0&onlineBonus=0&emp=0&locale=ru&lang=ru&curr=rub&couponsGeo=12,3,18,15,21&dest=-1029256,-102269,-1278703,-1255563&{query}&page={page}&sort=popular"
            # url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?curr=rub&dest=-1029256,-102269,-1278703,-1255563&lang=ru&locale=ru&page={page}&query={query}&resultset=catalog&sort=popular&spp=26"
            url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&couponsGeo=12,3,18,15,21&curr=rub&dest=-1029256,-102269,-1278703,-1255563&emp=0&lang=ru&locale=ru&page={page}&pricemarginCoeff=1.0&query={query}&reg=1&regions=68,64,83,4,38,80,33,70,82,86,75,30,69,22,66,31,40,1,48,71&resultset=catalog&sort=popular&spp=26&suppressSpellcheck=false"
            response = requests.get(url, proxies=proxy)
            response = json.loads(response.content)
            if "data" in response and response["data"]["products"]:
                for i, v in enumerate(response["data"]["products"]):
                    if str(sku) == str(v["id"]):
                        i += 1
                        return [page, i]
            else:
                break
        return None


def get_cpm(key, type_ad):
    wb_api = WbAPI()
    try:
        print("get_cpm", key, type_ad)
        if type_ad == "keyphrase":
            cpm_list = wb_api.catalog_ads(key)
        elif type_ad == "sku":
            cpm_list = wb_api.catalog_ads_sku(key)
        return cpm_list
    except:
        return "not found"


def wb_check_code_runner(data):
    buyouts_id_list = data["buyouts_id_list"]
    anwser = []
    for buyout_id in buyouts_id_list:

        response = ProductBuyout.objects.select_related("product").filter(id=buyout_id)[
            0
        ]
        status = response.status
        if status != "error":
            phone = response.phone
            sku = response.product.sku
            logger.info(phone, sku)

            if phone:
                response = Account.objects.all().filter(number=phone)[0]
                cookie = response.WILDAUTHNEW_V3
                if cookie:
                    wb_api = WbAPI()
                    wb_client_api = WbClientAPI(cookie)
                    response = wb_client_api.get_orders()
                    for active in response["value"]["active"]:
                        if "products" in active:
                            for product in active["products"]:
                                item_for_awnser = {"phone": phone, "item": product}
                                anwser.append(item_for_awnser)
                                logger.error(product)
                                if product["code1S"] == sku:
                                    delivery_description = product["trackingStatus"]
                                    logger.error(delivery_description)
                                    if delivery_description == "Готов к выдаче":
                                        delivery_description = (
                                            delivery_description + " " + ["expireDate"]
                                        )
                                        logger.error(delivery_description)
                                        current_status = "ready"
                                        if status != current_status:
                                            # ProductBuyout.objects.filter(id=buyout_id).update(status=current_status).update(delivery_description=delivery_description)
                                            logger.error(
                                                f"Status was updated to {status} {buyout_id}"
                                            )

    response = {"value": anwser}
    return response
