import json
import random
import re

import requests
from loguru import logger

from apps.home.helper import Helper
from apps.home.models import ClientPvz, ProductBuyout
from apps.home.services.proxy import get_proxy


class WbClientAPI:
    def __init__(self, cookie) -> None:
        self.cookie = cookie
        self.proxy = get_proxy()
        self.rout_js_version = self.get_rout_js_version()
        self.session = requests.Session()

    def get_rout_js_version(self):
        url = "https://www.wildberries.ru/"
        print("rout_js_version is")
        response = requests.get(url, proxies=self.proxy)
        rout_js_version = re.search(
            '(?<=\/\/static\.wbstatic\.net\/r\/route-data-ru\.js\?).*?(?=")',
            str(response.content),
        ).group()
        logger.debug(f"rout_js_version is {rout_js_version}")
        return rout_js_version  # "9.3.26"

    def account_profile_detail(self):
        url = "https://www.wildberries.ru/webapi/personalinfo"
        headers = {
            "Cookie": self.cookie,
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(url, headers=headers, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def get_balance(self):
        url = "https://www.wildberries.ru/webapi/account/getbalance"
        headers = {
            "Cookie": self.cookie,
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(url, headers=headers, proxies=self.proxy, timeout=15)
        response = json.loads(response.text)
        return response

    def add_to_basket(self, keys):
        url = "https://ru-basket-api.wildberries.ru/product/addtobasketsimple"
        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        body = f"cod1S={keys['cod1S']}&characteristicId={keys['characteristicId']}&priceWithCouponAndDiscount={keys['priceWithCouponAndDiscount']}&quantity={keys['basketQuantity']}&subjectId={keys['subjectId']}&subjectParentId={keys['subjectParentId']}"
        response = self.session.post(url, headers=headers, data=body, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def increase_basket_quantity(self, keys):
        url = "https://www.wildberries.ru/lk/basket/spa/recalc"
        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        body = f"paymentTypeId=79&prevPaymentTypeId=79&deliveryWay=self&noneIncludedInOrder=false&addressId=18395&isBuyItNowMode=false&unloadCargoOption=&chrtId=8675800&quantity={keys['basketQuantity']}&basketItemId=8675800"
        response = requests.post(url, headers=headers, data=body, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def get_basket(self):
        url = "https://ru-basket-api.wildberries.ru/lk/basket/items"
        headers = {
            "Cookie": self.cookie,
        }
        r = self.session.post(url, headers=headers, proxies=self.proxy)
        response = r.json()
        if not response["value"]:
            return []
        if response["value"] == 'Возникла ошибка при попытке загрузить корзину.':
            return []
        data = {
            "basketItems[0][targetUrl]": response["value"][0]["targetUrl"],
            "basketItems[0][cod1S]": response["value"][0]["cod1S"],
            "basketItems[0][quantity]": response["value"][0]["quantity"],
            "basketItems[0][chrtId]": response["value"][0]["characteristicId"],
            "useClientBasket": True,
        }
        url = "https://ru-basket-api.wildberries.ru/lk/basket/data?"

        response = self.session.post(url, headers=headers, proxies=self.proxy, data=data)
        response = json.loads(response.text)
        return response

    def qr_pay(self, data):
        url = "https://ru-basket-api.wildberries.ru/lk/basket/spa/submitorder"
        files = {
            "orderDetails.DeliveryPointId": (None, str(data["DeliveryPointId"])),
            "orderDetails.DeliveryWay": (None, "self"),
            "orderDetails.DeliveryPrice": (None, None),
            "orderDetails.PaymentType.Id": (None, 79),
            "orderDetails.MaskedCardId": (None, None),
            "orderDetails.SberPayPhone": (None, None),
            "orderDetails.ForcePay": (None, None),
            "orderDetails.AgreePublicOffert": (None, "true"),
            "orderDetails.TotalPrice": (None, str(data["TotalPrice"])),
            "orderDetails.UserBasketItems[0].priceWithCouponAndDiscount": (
                None,
                str(data["TotalPrice"]),
            ),
            "orderDetails.UserBasketItems[0].cod1S": (None, str(data["cod1S"])),
            "orderDetails.UserBasketItems[0].characteristicId": (
                None,
                str(data["characteristicId"]),
            ),
            "orderDetails.UserBasketItems[0].quantity": (None, str(data["quantity"])),
            "orderDetails.UserBasketItems[0].targetUrl": (None, str(data["targetUrl"])),
            # "orderDetails.UserBasketItems.Index": (None, 0),
            # "orderDetails.UserBasketItems[0].CharacteristicId": (
            #     None,
            #     str(data["IncludeInOrder"]),
            # ),
            "orderDetails.IncludeInOrder[0]": (None, str(data["IncludeInOrder"])),
            "orderDetails.UnloadCargoOption": (None, None),
        }
        headers = {
            "Cookie": self.cookie,
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = self.session.post(url, headers=headers, files=files, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def card_pay(self, data):
        url = "https://ru-basket-api.wildberries.ru/lk/basket/spa/submitorder"
        files = {
            #"orderDetails.AgreeToReceiveEmailSpam": (None, "false"),
            "orderDetails.DeliveryPointId": (None, str(data["DeliveryPointId"])),
            "orderDetails.DeliveryWay": (None, "self"),
            "orderDetails.DeliveryPrice": (None, 0),
            "orderDetails.PaymentType.Id": (None, 63),
            #"orderDetails.MaskedCardId": (None, None),  # ['paymentType']['id']
            #"orderDetails.SberPayPhone": (None, None),
            "orderDetails.forcePay": (None, "true"),  # this work just with tied card
            #"orderDetails.AgreePublicOffert": (None, "true"),
            "orderDetails.TotalPrice": (None, str(data["TotalPrice"])),
            #"orderDetails.IncludeInOrder[0]": (None, str(data["IncludeInOrder"])),
            "orderDetails.UnloadCargoOption": (None, None),
            "orderDetails.UserBasketItems[0].priceWithCouponAndDiscount": (
                None,
                str(data["TotalPrice"]),
            ),
            "orderDetails.UserBasketItems[0].cod1S": (None, str(data["cod1S"])),
            "orderDetails.UserBasketItems[0].characteristicId": (
                None,
                str(data["characteristicId"]),
            ),
            "orderDetails.UserBasketItems[0].quantity": (None, str(data["quantity"])),
            "orderDetails.UserBasketItems[0].targetUrl": (None, str(data["targetUrl"])),
            "orderDetails.currencyCodeIso": (None, "643")
        }
        headers = {
            "Cookie": self.cookie,
            "x-spa-version": self.rout_js_version,
            "sec-ch-ua-platform": "Windows",
            "sec-ch-ua": '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }
        response = self.session.post(url, headers=headers, files=files, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def address_remove(self, id):
        # url = "https://www.wildberries.ru/spa/removeaddress"
        url = "https://ru-basket-api.wildberries.ru/spa/removeaddress"
        data = f"addressId={id}&deliveryWay=self"
        headers = {
            "Cookie": self.cookie,
            "x-spa-version": self.rout_js_version,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        response = self.session.post(url, headers=headers, data=data, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def basket_clear(self, id):
        url = "https://ru-basket-api.wildberries.ru/lk/basket/spa/delete/simple"
        data = f"chrtIds%5B0%5D={id}"
        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        response = requests.post(url, headers=headers, data=data, proxies=self.proxy)
        if response.status_code == 200:
            response = json.loads(response.text)
        else:
            response = None
        return response

    def address_remove(self, id):
        url = "https://ru-basket-api.wildberries.ru/spa/removeaddress"
        data = f"addressId={id}&deliveryWay=self"
        headers = {
            "Cookie": self.cookie,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Windows",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(url, headers=headers, data=data, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def address_add(self, id, buyout_id):
        pvz_available = True
        url = "https://ru-basket-api.wildberries.ru/spa/poos/create?version=1"
        data = f"Item.AddressId={id}"
        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            # "x-requested-with": "XMLHttpRequest",
            # "x-spa-version": "9.2.23",
        }
        response = self.session.post(url, headers=headers, data=data, proxies=self.proxy)
        if response.status_code != 200:
            return False
        response = response.json()
        if 'value' in response and 'closedMsg' in response['value'][0]:
            pvz_available = False
        if response["resultState"] == -1 or not pvz_available:
            buyout = ProductBuyout.objects.get(id=buyout_id)
            clients_pvz = ClientPvz.objects.filter(client_id=buyout.client).order_by(
                "?"
            )
            for client_pvz in clients_pvz:
                address_id = client_pvz.pvz.status
                data = f"Item.AddressId={address_id}"
                headers = {
                    "Cookie": self.cookie,
                    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                }
                response = self.session.post(
                    url, headers=headers, data=data, proxies=self.proxy
                ).json()
                if 'value' in response and 'closedMsg' in response['value'][0]:
                    continue
                if response["resultState"] == 0:
                    buyout.pvz = client_pvz.pvz
                    buyout.save()
                    pvz_available = True
                    break
            else:
                return False
        if response["resultState"] == -1 or not pvz_available:
            return False
        return response

    def get_orders(self):
        url = "https://www.wildberries.ru/webapi/lk/myorders/delivery/active"
        headers = {
            "Cookie": self.cookie,
            "x-spa-version": self.rout_js_version,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }
        response = requests.post(url, headers=headers, proxies=self.proxy, timeout=50)
        response = json.loads(response.text)
        return response

    def add_review(self, data):
        # url = "https://www.wildberries.ru/product/comments"
        url = "https://www.wildberries.ru/webapi/product/comments"

        data = {
            "rating": data["rating"],
            "cod1s": data["cod1s"],
            "link": data["link"],
            "sizeMatch": data["sizeMatch"],
            "sizeName": data["sizeName"],
            "visibility": data["visibility"],
            "text": data["text"],
            "userPhotos": data["userPhotos"],
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
            "sec-ch-ua-mobile": "?0",
            "Connection": "keep-alive",
            "Cookie": self.cookie,
            # "sec-ch-ua-platform": "Windows",
            "Content-Type": "application/json",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(url, headers=headers, json=data, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def check_review(self, sku):
        url = f"https://www.wildberries.ru/webapi/product/comments/goods?nmId={sku}"
        headers = {
            "Cookie": self.cookie,
            # "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        r = requests.post(url, headers=headers, timeout=15, proxies=self.proxy)
        try:
            if r.json()["value"] == "У Вас уже есть (был) отзыв по данному товару":
                return True
        except:
            return False
        return False

    def delete_review(self, data):
        url = "https://www.wildberries.ru/lk/discussion/feedback/delete"

        data = "commentId=AdN10YABaOM9ENKQ1p-I&link=12059766"

        headers = {
            "Cookie": self.cookie,
            "x-spa-version": self.rout_js_version,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        response = requests.post(url, headers=headers, data=data, proxies=self.proxy)
        response = json.loads(response.text)
        logger.debug(f"{response}")
        return response

    def add_favorite(self, data):
        url = "https://www.wildberries.ru/webapi/lk/favorites/addtoponed"

        data = f"cod1S={data['cod1S']}&quantity=1&targetUrl=SP&targetCode=0&lw=IT&l=SHS&t={data['t']}&t1=&t2=&iid=1&characteristicId={data['characteristicId']}"
        print(data)

        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
            "x-last-fav-sync": "1654435692037",
        }
        response = requests.post(url, headers=headers, data=data, proxies=self.proxy)
        logger.debug(f"{response}")
        response = json.loads(response.text)
        return response

    def add_favorite_brand(self, brandId):
        url = "https://www.wildberries.ru/webapi/lk/favorites/brand/addbyid"

        data = f"brandId={brandId}"
        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(url, headers=headers, data=data, proxies=self.proxy)
        response = json.loads(response.text)
        logger.debug(f"{response}")
        return response

    def add_favorite_review(self, data):
        url = "https://www.wildberries.ru/webapi/product/comments/vote"

        data = f"id={data['id']}&vote={data['vote']}&link={data['link']}"

        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(url, headers=headers, data=data, proxies=self.proxy)
        response = json.loads(response.text)
        logger.debug(f"{response}")
        return response

    def add_question(self, token, data):
        url = "https://questions.wildberries.ru/api/v1/question"

        headers = {
            "authorization": "Bearer" + " " + token,
            "content-type": "application/json",
            # "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
            # "referer": "https://www.wildberries.ru/catalog/72865394/detail.aspx?targetUrl=XS",
        }
        print(headers)
        print(data)
        response = self.session.post(url, headers=headers, json=data, proxies=self.proxy)
        response = json.loads(response.text)
        logger.debug(f"{response}")
        return response

    def get_profile(self):
        url = "https://www.wildberries.ru/webapi/lk/details/data"
        data = "cardId=&paymentCode=crd"
        headers = {
            "Cookie": self.cookie,
            "content-type": "content-type: application/json; charset=utf-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(url, headers=headers, data=data, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def get_cards(self):
        url = "https://ru-basket-api.wildberries.ru/webapi/lk/bankcards"
        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(
            url, headers=headers, proxies=self.proxy, timeout=10
        )
        response = json.loads(response.text)
        return response

    def delete_card(self, card_id):
        # url = "https://www.wildberries.ru/webapi/lk/account/spa/deletecard"
        url = "https://ru-basket-api.wildberries.ru/webapi/lk/account/spa/deletecard"
        data = f"cardId={card_id}&paymentCode=crd"
        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(
            url, headers=headers, data=data, proxies=self.proxy, timeout=10
        )
        response = json.loads(response.text)
        logger.debug(f"{response}")
        return response

    def order_cancel(self, rId):
        url = "https://www.wildberries.ru/webapi/lk/myorders/delivery/cancel"
        data = f"rids={rId}"
        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(url, headers=headers, data=data, proxies=self.proxy)
        response = json.loads(response.text)
        logger.debug(f"{response}")
        return response

    def get_order(self, orderId):
        url = f"https://www.wildberries.ru/webapi/lk/order/confirmed/data?orderId={orderId}"
        headers = {
            "Cookie": self.cookie,
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = requests.post(url, headers=headers, proxies=self.proxy)
        if response.status_code != 200:
            return None
        response = json.loads(response.text)
        return response

    def get_token(self):
        url = "https://www.wildberries.ru/webapi/gettoken"
        headers = {
            "Cookie": self.cookie,
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        response = self.session.get(url, headers=headers, proxies=self.proxy)
        header = response.headers["Set-Cookie"]
        token = re.findall("(?<=access_token=).*?(?=;)", header)[0]
        return token

    def search(self, query, sku):
        headers = {
            "Cookie": self.cookie,
            "x-requested-with": "XMLHttpRequest",
            "x-spa-version": self.rout_js_version,
        }
        url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&couponsGeo=12,3,18,15,21&curr=rub&dest=-1029256,-102269,-446092,-431464&emp=0&lang=ru&locale=ru&pricemarginCoeff=1.0&query={query}&reg=1&regions=68,64,83,4,38,80,33,70,82,86,75,30,69,1,48,22,66,31,40,71&resultset=catalog&sort=popular&spp=27&suppressSpellcheck=false"
        response = self.session.get(url, proxies=self.proxy)
        url = f"https://www.wildberries.ru/catalog/{sku}/detail.aspx?targetUrl=MS"
        response = self.session.get(url, proxies=self.proxy)
        # response = json.loads(response.text)
        # return response


class WbAPI:
    def __init__(self) -> None:
        self.proxy = get_proxy()

    def wbxsearch(self, key_phrase):
        """return shardKey"""
        url = (
            f"https://wbxsearch.wildberries.ru/exactmatch/v2/common?query={key_phrase}"
        )
        response = requests.get(url, proxies=self.proxy)
        response = json.loads(response.content)
        shard_key = response["shardKey"]
        query = response["query"]
        return shard_key, query

    def wbxcatalog(self, shard_key, query, page=1):
        logger.error(shard_key, query)
        """ return ssubject, brands, goods """
        # url = f'https://wbxcatalog-ru.wildberries.ru/{shard_key}/catalog?spp=0&regions=69,64,86,83,75,4,38,30,33,70,71,22,31,66,68,82,48,1,40,80&stores=117673,122258,122259,125238,125239,125240,6159,507,3158,117501,120602,120762,6158,121709,124731,159402,2737,130744,117986,1733,686,132043&pricemarginCoeff=1.0&reg=0&appType=1&offlineBonus=0&onlineBonus=0&emp=0&locale=ru&lang=ru&curr=rub&couponsGeo=12,3,18,15,21&dest=-1029256,-102269,-1278703,-1255563&{query}'
        url = f"https://wbxcatalog-ru.wildberries.ru/{shard_key}/filters?filters=xsubject;fkind;fcolor;fbrand&spp=0&regions=69,64,86,83,75,4,38,30,33,70,71,22,31,66,68,82,48,1,40,80&stores=117673,122258,122259,125238,125239,125240,6159,507,3158,117501,120602,120762,6158,121709,124731,159402,2737,130744,117986,1733,686,132043&pricemarginCoeff=1.0&reg=0&appType=1&offlineBonus=0&onlineBonus=0&emp=0&locale=ru&lang=ru&curr=rub&couponsGeo=12,3,18,15,21&dest=-1029256,-102269,-1278703,-1255563&{query}"
        response = requests.get(url, proxies=self.proxy)
        response = json.loads(response.content)
        ssubject = response["data"]["filters"][0]["items"][0]["id"]
        brands = []
        for id in response["data"]["filters"][3]["items"]:
            brands.append(id["id"])
        return ssubject, brands

    def catalog_ads(self, key_phrase):
        params = {"keyword": key_phrase}
        url = f"https://catalog-ads.wildberries.ru/api/v5/search"
        response = requests.get(url, params=params, proxies=self.proxy)
        resp_data = response.json()
        if "pages" in resp_data:
            page1_positions = resp_data["pages"][0]["positions"]
            page2_positions = resp_data["pages"][1]["positions"]
            cpm_list = []
            for i in range(0, len(page1_positions) + len(page2_positions)):
                item = resp_data["adverts"][i]
                if i < len(page1_positions):
                    page = 1
                    position = page1_positions[i]

                else:
                    page = 2
                    position = page2_positions[i - len(page1_positions)]
                sku = item["id"]
                link = f"https://www.wildberries.ru/catalog/{sku}/detail.aspx"
                cover = (
                    cover
                ) = f"https://images.wbstatic.net/big/new/{str(sku)[:-4]}0000/{sku}-1.jpg"
                name = Helper.check_sku(item["id"], 1)["title"]
                cpm_list.append(
                    {
                        "sku": item["id"],
                        "name": name,
                        "cpm": item["cpm"],
                        "position": position,
                        "link": link,
                        "page": page,
                        "cover": cover,
                    }
                )
            cpm_list = sorted(cpm_list, key=lambda d: d["position"])
            print(cpm_list)
            return cpm_list

    def catalog_ads_sku(self, sku):
        params = {"nm": sku}
        url = f"https://carousel-ads.wildberries.ru/api/v4/carousel"
        response = requests.get(url, params=params, proxies=self.proxy)
        resp_data = response.json()
        print(resp_data)
        if len(resp_data) > 0:
            cpm_list = []
            for i in range(0, len(resp_data)):
                item = resp_data[i]
                if i < int(len(resp_data) / 2):
                    page = 1

                else:
                    page = 2
                sku = item["nmId"]
                link = f"https://www.wildberries.ru/catalog/{sku}/detail.aspx"
                cover = (
                    cover
                ) = f"https://images.wbstatic.net/big/new/{str(sku)[:-4]}0000/{sku}-1.jpg"
                name = Helper.check_sku(sku, 1)["title"]
                cpm_list.append(
                    {
                        "sku": sku,
                        "name": name,
                        "cpm": item["cpm"],
                        "position": item["position"],
                        "link": link,
                        "page": page,
                        "cover": cover,
                    }
                )
            cpm_list = sorted(cpm_list, key=lambda d: d["position"])
            print(cpm_list)
            return cpm_list

    def wbxcatalog_nm(self, nms):
        url = f"https://card.wb.ru/cards/detail?spp=24&regions=68,64,83,4,38,80,33,70,82,86,75,30,69,22,66,31,40,1,48,71&pricemarginCoeff=1.0&reg=1&appType=1&emp=0&locale=ru&lang=ru&curr=rub&couponsGeo=12,3,18,15,21&dest=-1029256,-102269,-1278703,-1255563&nm={nms}"
        response = requests.get(url, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def get_brandId(self, url):
        try:
            response = requests.get(url, proxies=self.proxy)
            return response.json()
        except:
            return False

    def get_cards_detail(self, nm):
        url = f"https://card.wb.ru/cards/detail?spp=15&regions=68,64,83,4,38,80,33,70,82,86,30,69,22,66,31,48,1,40&pricemarginCoeff=1.0&reg=1&appType=1&emp=0&locale=ru&lang=ru&curr=rub&stores=130744,117501,507,3158,204939,120762,117986,159402,2737,686,1733&couponsGeo=2,7,3,6,19,21,8&dest=-1059500,-108082,-365233,-1116490&nm={nm}"
        response = requests.get(url, proxies=self.proxy)
        logger.debug(response.text)
        response = json.loads(response.text)
        return response

    def get_reviews(self, data):
        # url = "https://public-feedbacks.wildberries.ru/api/v1/summary/full"
        # url = "https://feedbacks.wildberries.ru/api/v1/feedbacks/site"
        url = "https://feedbacks.wildberries.ru/api/v1/summary/full"
        proxy_list = [
            "http://QFFXv1KH:j3KrcVKm@45.145.88.160:64617",
            "http://QFFXv1KH:j3KrcVKm@212.192.228.245:51677",
            "http://QFFXv1KH:j3KrcVKm@5.101.65.213:59035",
            "http://QFFXv1KH:j3KrcVKm@84.54.31.85:56864",
            "http://QFFXv1KH:j3KrcVKm@194.156.116.93:45877",
            "http://QFFXv1KH:j3KrcVKm@109.94.210.252:61076",
            "http://QFFXv1KH:j3KrcVKm@45.134.25.117:49532",
            "http://QFFXv1KH:j3KrcVKm@92.249.12.188:51198",
            "http://QFFXv1KH:j3KrcVKm@87.247.141.130:54736",
            "http://QFFXv1KH:j3KrcVKm@91.188.230.40:46664",
            "http://QFFXv1KH:j3KrcVKm@45.146.171.161:57076",
            "http://QFFXv1KH:j3KrcVKm@45.150.61.166:48132",
            "http://QFFXv1KH:j3KrcVKm@45.148.240.93:61578",
            "http://QFFXv1KH:j3KrcVKm@45.143.142.249:64655",
            "http://QFFXv1KH:j3KrcVKm@45.135.177.18:53081",
            "http://QFFXv1KH:j3KrcVKm@193.232.88.142:51278",
            "http://QFFXv1KH:j3KrcVKm@195.19.169.137:64340",
            "http://QFFXv1KH:j3KrcVKm@195.19.170.150:57751",
            "http://QFFXv1KH:j3KrcVKm@195.208.89.213:63973",
            "http://QFFXv1KH:j3KrcVKm@195.208.92.230:55816",
        ]
        proxy_one = random.choice(proxy_list)
        proxy = {"http": proxy_one, "https": proxy_one}
        data = {
            "imtId": data["imtId"],
            "skip": data["skip"],
            "take": data["take"],
            "order": "dateDesc",
        }
        response = requests.post(url, json=data, proxies=proxy)
        response = json.loads(response.text)
        return response

    def get_good(self, sku):
        url = f"https://wbx-content-v2.wbstatic.net/ru/{sku}.json"
        response = requests.get(url, proxies=self.proxy)
        response = json.loads(response.text)
        return response

    def get_item_characters(self, sku):
        part = sku[: len(sku) - 3]
        vol = sku[: len(sku) - 5]
        print(part, vol)
        for i in range(1, 10):
            url = (
                f"https://basket-0{i}.wb.ru/vol{vol}/part{part}/{sku}/info/ru/card.json"
            )
            response = requests.get(url, proxies=self.proxy)
            if response.status_code == 200:
                response = json.loads(response.text)
                return response

    def get_search(self, phrase):
        url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&couponsGeo=12,3,18,15,21&curr=rub&dest=-1029256,-102269,-2162196,-1257786&emp=0&lang=ru&locale=ru&pricemarginCoeff=1.0&query={phrase}&reg=0&regions=68,64,83,4,38,80,33,70,82,86,75,30,69,1,48,22,66,31,40,71&resultset=filters&spp=0&suppressSpellcheck=false"
        response = requests.get(url, proxies=self.proxy)
        try:
            response = json.loads(response.text)
            return response
        except:
            return None


class WbHepler:
    @staticmethod
    def get_part_review(skip, order, has_photo, sku):
        proxy_list = [
            "http://QFFXv1KH:j3KrcVKm@45.145.88.160:64617",
            "http://QFFXv1KH:j3KrcVKm@212.192.228.245:51677",
            "http://QFFXv1KH:j3KrcVKm@5.101.65.213:59035",
            "http://QFFXv1KH:j3KrcVKm@84.54.31.85:56864",
            "http://QFFXv1KH:j3KrcVKm@194.156.116.93:45877",
            "http://QFFXv1KH:j3KrcVKm@109.94.210.252:61076",
            "http://QFFXv1KH:j3KrcVKm@45.134.25.117:49532",
            "http://QFFXv1KH:j3KrcVKm@92.249.12.188:51198",
            "http://QFFXv1KH:j3KrcVKm@87.247.141.130:54736",
            "http://QFFXv1KH:j3KrcVKm@91.188.230.40:46664",
            "http://QFFXv1KH:j3KrcVKm@45.146.171.161:57076",
            "http://QFFXv1KH:j3KrcVKm@45.150.61.166:48132",
            "http://QFFXv1KH:j3KrcVKm@45.148.240.93:61578",
            "http://QFFXv1KH:j3KrcVKm@45.143.142.249:64655",
            "http://QFFXv1KH:j3KrcVKm@45.135.177.18:53081",
            "http://QFFXv1KH:j3KrcVKm@193.232.88.142:51278",
            "http://QFFXv1KH:j3KrcVKm@195.19.169.137:64340",
            "http://QFFXv1KH:j3KrcVKm@195.19.170.150:57751",
            "http://QFFXv1KH:j3KrcVKm@195.208.89.213:63973",
            "http://QFFXv1KH:j3KrcVKm@195.208.92.230:55816",
        ]
        proxy_one = random.choice(proxy_list)
        proxy = {"http": proxy_one, "https": proxy_one}
        data = WbHepler.cards_detail_request(sku)
        ssrModel = data["data"]["products"][0]["root"]

        params = {
            "imtId": ssrModel,
            "skip": skip,
            "take": 20,
            "order": order,
            # "hasPhoto": True if has_photo == "true" else False,
        }
        if has_photo == "true":
            params["hasPhoto"] = True

        r = requests.post(
            "https://feedbacks.wildberries.ru/api/v1/feedbacks/site",
            data=json.dumps(params),
            proxies=proxy,
        )
        return r.json()

    @staticmethod
    def cards_detail_request(sku):
        proxy = get_proxy()
        r = requests.get(
            #f"https://card.wb.ru/cards/detail?spp=24&regions=68,64,83,4,38,80,33,70,82,86,75,30,69,22,66,31,40,1,48,71&pricemarginCoeff=1.0&reg=1&appType=1&emp=0&locale=ru&lang=ru&curr=rub&couponsGeo=12,3,18,15,21&dest=-1029256,-102269,-1278703,-1255563&nm={sku}",
            f"https://card.wb.ru/cards/detail?spp=28&regions=80,64,83,4,38,33,70,82,69,68,86,75,30,40,48,1,22,66,31,71&pricemarginCoeff=1.0&reg=1&appType=1&emp=0&locale=ru&lang=ru&curr=rub&couponsGeo=12,3,18,15,21&sppFixGeo=4&dest=-1029256,-102269,-2162196,-1257218&nm={sku}",
            proxies=proxy,
        )
        return r.json()

    @staticmethod
    def get_pvz_info():
        headers = {
            "Connection": "keep-alive",
            "x-spa-version": "9.3.45",
            "x-requested-with": "XMLHttpRequest",
        }
        pvz_ids_request = requests.get(
            "https://www.wildberries.ru/webapi/spa/modules/pickups",
            headers=headers,
            proxies=get_proxy(),
        )
        pvz_ids = pvz_ids_request.json()
        id_list = [pvz["id"] for pvz in pvz_ids["value"]["pickups"]]
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        pvz_address_request = requests.post(
            "https://www.wildberries.ru/webapi/poo/byids",
            data=json.dumps(id_list),
            headers=headers,
            proxies=get_proxy(),
        )
        return pvz_address_request.json(), pvz_ids
