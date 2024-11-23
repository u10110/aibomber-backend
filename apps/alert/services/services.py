import base64
import random
import re
import time as time_
import xml.etree.ElementTree as elementTree
from datetime import date, datetime, time, timedelta
from datetime import timezone as d_timezone

import requests
from django.db.models import Q
from django.utils import timezone
from loguru import logger
from PIL import Image, ImageOps

from apps.alert.services import wb_api
from apps.alert.services.sbp import get_sbp_links
from apps.billing.models import Limits
from apps.home.helper import Helper
from apps.home.models import (
    Account,
    AddingReview,
    BoostLike,
    BoostLikeReview,
    BoostQuestion,
    ClientProduct,
    ProductBuyout,
)
from apps.home.services.proxy import get_proxy
from core.settings import MEDIA_ROOT

from ..models import TgMessage, ZennoPoster
from . import helper
from .wb_api import WbAPI, WbClientAPI


class Eramp:
    def __init__(self) -> None:
        pass

    def add_sale(tg_chat_id, email, sale_id):
        date_end = date.today() + timedelta(days=30)
        print("Today's date:", date_end)
        ZennoPoster.objects.create(
            sale_id=sale_id, email=email, tg_chat_id=tg_chat_id, date_end=date_end
        )

    def get_sale(tg_chat_id, email):
        response = ZennoPoster.objects.all().filter(tg_chat_id=tg_chat_id)[0]
        sale_id = response.sale_id
        date_end = response.date_end
        return sale_id, date_end

    def update_date_end(tg_chat_id, date_end, days):
        date_end = date_end + timedelta(days=days)
        ZennoPoster.objects.filter(tg_chat_id=tg_chat_id).update(date_end=date_end)

    def isXml(value):
        try:
            elementTree.fromstring(value)
        except elementTree.ParseError:
            return False
        return True


class BuyoutManager(WbClientAPI):
    def __init__(self, data):
        self.buyout_id = data["buyout_id"]
        self.key_phrase = ProductBuyout.objects.get(id=self.buyout_id).key_phrase
        self.link_type = data["link_type"]
        self.sex = data["sex"]
        self.nms = data["sku"]
        self.basketQuantity = 1
        self.AddressId = data["AddressId"]
        self.pay_checker = data["Pay_checker"]
        self.wb_api = WbAPI()
        self.proxy = get_proxy()
        self.rout_js_version = super().get_rout_js_version()
        self.session = requests.Session()

        self.buyout = ProductBuyout.objects.filter(id=self.buyout_id)[0]

    def get_pay_link(self):
        """
        1. Get Account
        2. Check Account
        3. Clear basket
        4. Add to basket
        5. Remove address
        6. Add address
        7. Get link qr/card pay
        8. Run schedule pay checker
        """
        for attempt in range(0, 10):
            self.account = self.get_account()
            if not self.account:
                logger.error("No free accounts")
                return None

            product = Helper.check_sku(self.nms, 1)
            if product == False:
                return {"resp": "stock"}
            logger.info(f"Get account {self.account}")

            if not self.is_valid_account(self.account):
                logger.warning(f"Account {self.account.id} is not valid")
                continue

            if self.is_not_buyed_account():
                if self.buyout.payment_link and self.buyout.phone:
                    return self.buyout.payment_link
                logger.warning(f"Account {self.account.id} is have not payed orders")
                Account.objects.filter(id=self.account.id).update(status="free")
                continue

            response = super().get_balance()
            balance = response["value"]["moneyBalance"]
            if balance > 0:
                Account.objects.filter(number=self.account.number).update(
                    status="balance"
                )
                logger.warning(f"Account {self.account.id} have balance")
                continue

            self.basket_clear_()
            self.delete_card()

            super().search(self.key_phrase, self.nms)

            response = self.add_to_basket_()
            self.address_remove_(response)

            response = super().address_add(self.AddressId, self.buyout_id)
            if not response:
                logger.error(f"Not available pvz")
                return "Not available pvz"

            link = self._get_pay_link()
            if self.link_type == "qr":
                self.price_buy = int(re.findall("(?<=&sum=).*?(?=&)", link)[0]) // 100
            elif self.link_type == "sbp":
                pass
            else:
                self.price_buy = int(re.findall("(?<=/sum/).*?(?=/)", link)[0]) // 100

            if self.pay_checker == "yes":
                data = {
                    "buyout_id": self.buyout_id,
                    "code1s": self.code1s,
                    "wb_client_api": self.cookie,
                    "orderId": self.orderId,
                }
                url = "http://192.168.122.200:4440//api/40/webhook/Z4vpTd4idADjiM9pUzIadxsa4XksTPK1#pay_checker"
                r = requests.post(url, json=data)

            self.save(link)
            if not link:
                logger.error(f"Can not get pay link")
                return None
            else:
                return link

    def delete_card(self):
        request = super().get_cards()
        logger.debug(f"{request}")
        for card in request["value"]["maskedCards"]:
            super().delete_card(card["id"])

    def save(self, link):

        date_now = datetime.now(d_timezone.utc)
        # limits = Limits.objects.get(
        #     client_id=self.buyout.client_id,
        #     start_date__lte=date_now,
        #     end_date__gte=date_now,
        # )
        # limits.buyout_limit -= 1
        # limits.save()

        ProductBuyout.objects.filter(id=self.buyout_id).update(
            buyout_date=date_now,
            phone=self.account.number,
            full_name=self.account.full_name,
            price_buy=self.price_buy,
            rId=self.rId,
            orderId=self.orderId,
            payment_link=link,
        )
        Account.objects.filter(id=self.account.id).update(status="free")
        logger.info(f"DB was updated db")

    def get_account(self):

        phones_spent = []
        buyout = ProductBuyout.objects.get(id=self.buyout_id)

        if buyout.phone:
            account = Account.objects.filter(number=buyout.phone)[0]
            self.cookie = account.WILDAUTHNEW_V3
            print(f"YES {account}")
            return account
        sku_buyouts = ProductBuyout.objects.filter(product=buyout.product)
        account_delivery = ProductBuyout.objects.filter(
            Q(status="delivery") | Q(status="ready")
        )

        for buyout in sku_buyouts:
            if buyout.phone != None:
                phones_spent.append(buyout.phone)
        for buyout in account_delivery:
            if buyout.phone != None:
                phones_spent.append(buyout.phone)

        accounts = (
            Account.objects.filter(sex=self.sex, status="free")
            .exclude(WILDAUTHNEW_V3__isnull=True)
            .exclude(WILDAUTHNEW_V3__exact="")
            .exclude(number__in=phones_spent)
        )

        account = accounts[random.randint(0, len(accounts) - 1)]
        print(account.number)
        r = Account.objects.filter(id=account.id).update(status="work")
        print(r)
        self.cookie = account.WILDAUTHNEW_V3

        return account

    def is_valid_account(self, account):
        response = super().account_profile_detail()
        # logger.debug(f"Response is_valid_account {response}")
        if response["value"]["isAuthenticated"] is not True:
            logger.error(f"{account.id} bad account")
            response = Account.objects.filter(id=account.id).update(
                status="bad account"
            )
            return False
        else:
            return True

    def is_not_buyed_account(self):
        response = super().get_orders()
        for item in response["value"]["positions"]:
            if not item["isPrepaid"] and item["trackingStatus"] != "Отмена":
                return True
        return False

    def _get_product_price(self):
        priceWithCouponAndDiscount = ""
        response = self.wb_api.wbxcatalog_nm(self.nms)
        self.code1s = response["data"]["products"][0]["id"]

        # if "extended" in response["data"]["products"][0]:
        # if "clientPriceU" in response["data"]["products"][0]["extended"]:
        # priceWithCouponAndDiscount = response["data"]["products"][0][
        # "extended"
        # ]["clientPriceU"]
        if priceWithCouponAndDiscount == "":
            priceWithCouponAndDiscount = response["data"]["products"][0]["salePriceU"]
        priceWithCouponAndDiscount = priceWithCouponAndDiscount / 100
        return response, priceWithCouponAndDiscount

    def _product_detail_serializer(self, response, price):
        size_optionId = ""

        for size in response["data"]["products"][0]["sizes"]:
            print(size)
            if self.buyout.size == size["origName"]:
                size_optionId = size["optionId"]
                break

        data = {
            "cod1S": response["data"]["products"][0]["id"],
            # get SIZE
            "characteristicId": size_optionId,
            "priceWithCouponAndDiscount": price,
            "subjectId": response["data"]["products"][0]["subjectId"],
            "subjectParentId": response["data"]["products"][0]["subjectParentId"],
            "basketQuantity": self.basketQuantity,
        }
        return data

    def basket_clear_(self):
        response = super().get_basket()

        if "value" in response:
            for id in response["value"]["data"]["basket"]["includeInOrder"]:
                self.basket_clear(id)

    def add_to_basket_(
        self,
    ):
        response, price = self._get_product_price()
        self.price_buy = price
        data = self._product_detail_serializer(response, price)
        response = super().add_to_basket(data)
        return response

    def address_remove_(self, response):
        while True:
            # for removing addresses
            response = self.get_basket()
            if not response:
                raise Exception(
                    "| Empty response get basket - address remove function |"
                )
            if (
                "selectedAddressId"
                in response["value"]["data"]["basket"]["deliveryWays"][0]
            ):
                address = response["value"]["data"]["basket"]["deliveryWays"][0][
                    "selectedAddressId"
                ]
                self.address_remove(address)
            else:
                break

    def _get_pay_link(
        self,
    ):
        response = super().get_basket()
        data, price = self._address_add_serializer(response)

        logger.debug(f"{data}")
        if self.link_type == "qr" or self.link_type == "sbp":
            response = super().qr_pay(data)
            if "url" in response["value"]:
                link = response["value"]["url"]
                if link == "/lk/payment/fail":
                    raise Exception("| Payment fail QR pay |")
                link = re.findall("https://qr\.nspk\.ru.*?(?=&redirectUrl)", link)[0]
                logger.info(f"true account {self.account.id}")
                if self.link_type == "sbp":
                    self.price_buy = (
                        int(re.findall("(?<=&sum=).*?(?=&)", link)[0]) // 100
                    )
                    link = get_sbp_links(link)
            else:
                link = None
                logger.info(f"false account {self.account.id}")

        elif self.link_type == "card":
            response = super().card_pay(data)
            logger.debug(f"{response}")
            if "url" in response["value"]:
                link = response["value"]["url"]
            else:
                link = None
        self.rId = self.get_rid()
        if self.link_type == "card":
            self.orderId = response["value"]["data"]["positions"][0]["orderId"]
        else:
            checkUrl = response["value"]["checkUrl"]
            self.orderId = re.findall("(?<=orderId=).*?(?=&)", checkUrl)[0]

        return link

    def get_rid(self):

        for i in range(0, 2):
            time_.sleep(2)
            response = super().get_orders()
            for position in response["value"]["positions"]:
                if self.nms == position["code1S"]:
                    if position["rId"].isdigit():
                        return position["rId"]
                    else:
                        print(f"rId is not digit!")
                        break

    def _address_add_serializer(self, response):
        # for i, item in enumerate(
        #     response["value"]["data"]["basket"]["basketItems"][0]
        # ):
        item = response["value"]["data"]["basket"]["basketItems"][0]
        if self.nms == item["cod1S"]:
            data = {
                "DeliveryPointId": response["value"]["data"]["basket"]["deliveryWays"][
                    0
                ]["selectedAddressId"],
                "PaymentType": 79,  # 64 - картой, 79 - qr
                "TotalPrice": item["priceWithCouponAndDiscount"],
                "IncludeInOrder": item["id"],
                # "totalAvailableItemsCount": response["value"]["data"]["basket"][
                #     "totalAvailableItemsCount"
                # ],
                "cod1S": item["cod1S"],
                "characteristicId": item["characteristicId"],
                "quantity": item["quantity"],
                "targetUrl": item["targetUrl"],
            }

        if "priceWithCouponAndDiscount" in data:
            price = data["priceWithCouponAndDiscount"]
        else:
            price = data["TotalPrice"]
        if self.basketQuantity > 1:
            price = int(price) * self.basketQuantity  # for increase quantity
        return data, price


class ReivewManager(WbClientAPI):
    def __init__(self, review_id):
        self.review_id = review_id

        self.wb_api = WbAPI()
        self.proxy = get_proxy()
        self.review = AddingReview.objects.get(id=self.review_id)
        self.buyout = ProductBuyout.objects.get(id=self.review.buyout_id)
        self.product = ClientProduct.objects.get(id=self.buyout.product_id)
        self.account = Account.objects.filter(number=self.buyout.phone)[0]
        self.cookie = self.account.WILDAUTHNEW_V3
        self.size_list = []
        self.rout_js_version = super().get_rout_js_version()

        logger.debug(
            f"review is {self.review} {self.buyout.id} {self.product.id} {self.account.id}"
        )

    def add_review(self):
        check = super().check_review(self.product.sku)
        if check:
            self.result = {"resultState": "done"}
            self._update_status()
            return {"error": "already done"}
        self.link = self.get_link()
        if not self.link:
            self.result = None
            self._update_status()
            return {"error": "None request"}
        self.result = None
        logger.debug(f"size_list is {self.size_list}")
        self.size_list.append(self.buyout.size)
        for size in self.size_list:
            data = self._review_serialization(size)
            result = super().add_review(data)
            if (
                "ResultState" in result
                and result["Value"] == "Необходима авторизация пользователя"
            ):
                self.result = {"resultState": -2, "value": "Исключен из рейтинга"}
                break
            elif result["resultState"] == -1:
                self.result = result
            elif result["resultState"] == 0:
                self.result = result
                break
        self._update_status()
        return self.result

    def get_link(self):
        link = ""
        response = self.wb_api.wbxcatalog_nm(self.product.sku)
        logger.debug(f"{response}")
        for product in response["data"]["products"]:
            self.get_size(product)
            if str(product["id"]) == self.product.sku:
                link = product["root"]
        return link

    def get_size(self, product):
        logger.debug(f"{product}")
        for size in product["sizes"]:
            self.size_list.append(size["origName"])
        return product

    def _update_status(self):
        if not self.result:
            status = "error"
            status_description = "401 Error"
        elif self.result["resultState"] == "done":
            status = "done"
            status_description = "Размещен"
        elif self.result["resultState"] == -1:
            status = "error"
            status_description = self.result["value"]

        elif self.result["resultState"] == -2:
            status = "excluded"
            status_description = self.result["value"]

        elif self.result["resultState"] == 0:
            status = "done"
            status_description = "Размещен"

            date_now = datetime.now(d_timezone.utc)
            try:
                limits = Limits.objects.get(
                    client_id=self.review.client_id,
                    start_date__lte=date_now,
                    end_date__gte=date_now,
                )
            except:
                raise Exception("| User dont have limits |")
            limits.review_limit -= 1
            limits.save()
        date_now = datetime.now(d_timezone.utc)
        AddingReview.objects.filter(id=self.review_id).update(
            status=status, status_description=status_description, updated_at=date_now
        )

    def _review_serialization(self, size):

        image_encoded_list = self.get_image_list()
        if self.buyout.size:
            # sizeMatch = "ok"
            sizeMatch = "ok"
            sizeName = size
        else:
            # sizeMatch = ""
            sizeMatch = None
            sizeName = "0"
        data = {
            "rating": self.review.star,
            "cod1s": str(self.product.sku),
            "link": self.link,
            "sizeMatch": sizeMatch,
            "sizeName": str(sizeName),
            "visibility": 1,
            "text": self.review.text,
            "userPhotos": image_encoded_list,
        }
        return data

    def get_image_list(self):
        image_list = []
        image_encoded_list = []
        max_size = 674, 900  # max_width, max_height

        if self.review.image1:
            image_list.append(self.review.image1)
        if self.review.image2:
            image_list.append(self.review.image2)
        if self.review.image3:
            image_list.append(self.review.image3)
        if self.review.image4:
            image_list.append(self.review.image4)
        if self.review.image5:
            image_list.append(self.review.image5)

        if image_list:
            for image_path in image_list:
                logger.debug(f"{image_path}")

                image = Image.open(image_path)
                image = ImageOps.exif_transpose(image)
                print(image)
                print(image.size)
                image = image.convert("RGB")

                if (
                    image.size[0] > max_size[0]
                    or image.size[1] > max_size[1]
                    or image.size[0] < max_size[0]
                    or image.size[1] < max_size[1]
                ):

                    image.thumbnail(max_size, Image.ANTIALIAS)
                    print(image.size)

                    image.save(f"{MEDIA_ROOT}/{image_path}-resize.jpg", "JPEG")
                    image_path = rf"{MEDIA_ROOT}/{image_path}-resize.jpg"
                    print(image_path)

                    with open(image_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read())

                else:
                    encoded_string = base64.b64encode(image_path.read())

                image = encoded_string.decode("utf-8")
                image_encoded_list.append(image)
                # s = 2 / 0

        return image_encoded_list


class FavoriteManager(WbClientAPI):
    def __init__(self, favorite_id):
        self.favorite_id = favorite_id

        self.wb_api = WbAPI()
        self.proxy = get_proxy()

        self.favorite = BoostLike.objects.filter(id=self.favorite_id)[0]
        logger.debug(f"favorite is {self.favorite}")
        self.account = self.get_account()
        self.cookie = self.account.WILDAUTHNEW_V3
        self.rout_js_version = super().get_rout_js_version()
        logger.debug(f"account for favorite is {self.cookie}")

    def get_account(self):
        account_done = []
        favorites = BoostLike.objects.filter(url=self.favorite.url)
        for favorite in favorites:
            account_done.append(favorite.account_phone)
        account_all = (
            Account.objects.filter(status="free")
            .exclude(WILDAUTHNEW_V3__exact="")
            .exclude(WILDAUTHNEW_V3__isnull=True)
            .all()
        )
        # return account_all[1110]
        for account in account_all:
            if account.number not in account_done:
                return account

    def add_favorite(self):
        if self.favorite.url_type == "brand":
            brandId = re.findall("(?<=brands/).*?(?=-)", self.favorite.url)
            if brandId:
                brandId = brandId[0]
            if brandId and brandId.isdigit() and len(brandId) == 7:
                response = super().add_favorite_brand(brandId)
            else:
                brand = re.findall("(?<=brands/).*", self.favorite.url)[0]
                url = f"https://static.wbstatic.net/data/brands/{brand}.json"
                response = self.wb_api.get_brandId(url)
                if not response:
                    raise Exception("| Error brandId request |")
                brandId = response["id"]
                response = super().add_favorite_brand(brandId)

        elif self.favorite.url_type == "product":
            nms = re.findall("(?<=catalog/).*?(?=/)", self.favorite.url)[0]
            response = self.wb_api.wbxcatalog_nm(nms)
            code1S = response["data"]["products"][0]["id"]
            characteristicId = response["data"]["products"][0]["sizes"][0]["optionId"]
            data = {"cod1S": code1S, "t": "", "characteristicId": characteristicId}
            response = super().add_favorite(data)

        if "resultState" in response and response["resultState"] == 0:
            status = "done"

            date_now = datetime.now(d_timezone.utc)
            limits = Limits.objects.get(
                client_id=self.favorite.client_id,
                start_date__lte=date_now,
                end_date__gte=date_now,
            )
            limits.like_limit -= 1
            limits.save()

        else:
            status = "error"

        BoostLike.objects.filter(id=self.favorite.id).update(
            status=status, account_phone=self.account.number
        )
        return response


class QuestionManager(WbClientAPI):
    def __init__(self, question_id):
        self.question_id = question_id

        self.wb_api = WbAPI()
        self.proxy = get_proxy()

        self.question = BoostQuestion.objects.filter(id=self.question_id)[0]

        logger.debug(f"question is {self.question.question_text}")
        self.account = self.get_account()
        self.cookie = self.account.WILDAUTHNEW_V3
        self.rout_js_version = super().get_rout_js_version()
        self.session = requests.Session()
        logger.debug(f"account for question is {self.cookie}")

    def get_account(self):
        account_done = []
        start_time = datetime.combine(datetime.today(), time(00, 00, 00, 00))
        questions = BoostQuestion.objects.filter(
            Q(sku=self.question.sku) | Q(question_date__gte=start_time)
        )
        for question in questions:
            account_done.append(question.account_id)

        if self.question.sex is None:
            self.question.sex = 0
        account_all = (
            Account.objects.filter(status="free")
            .filter(sex=self.question.sex)
            .exclude(WILDAUTHNEW_V3__exact="")
            .exclude(WILDAUTHNEW_V3__isnull=True)
            .all()
        )
        for account in account_all:
            if account.id not in account_done:
                return account

    def is_valid_account(self, account):
        response = super().account_profile_detail()
        # logger.debug(f"Response is_valid_account {response}")
        if response["value"]["isAuthenticated"] is not True:
            logger.error(f"{account.id} bad account")
            response = Account.objects.filter(id=account.id).update(
                status="bad account"
            )
            return False
        else:
            return True

    def question_add(self):
        response = self.wb_api.get_cards_detail(self.question.sku)
        print(response)
        imtId = response["data"]["products"][0]["root"]

        response = self.wb_api.get_good(self.question.sku)
        goodsName = response["subj_name"]

        data = {
            "imtId": imtId,
            "nmId": int(self.question.sku),
            "text": self.question.question_text,
            "goodsName": goodsName,
        }

        for i in range(10):
            if not self.is_valid_account(self.account):
                BoostQuestion.objects.filter(id=self.question.id).update(
                    account_id=self.account.id
                )
                self.account = self.get_account()
                self.cookie = self.account.WILDAUTHNEW_V3
                continue
            token = super().get_token()
            response = super().add_question(token, data)
            if response and "ErrorCode" in response and response["ErrorCode"] == 403:
                BoostQuestion.objects.filter(id=self.question.id).update(
                    account_id=self.account.id
                )
                self.account = self.get_account()
                self.cookie = self.account.WILDAUTHNEW_V3
                continue
            break
        else:
            BoostQuestion.objects.filter(id=self.question.id).update(
                account_id=self.account.id, status="active"
            )
            return {"result": "error"}
        if response is None:
            status = "done"

            date_now = datetime.now(d_timezone.utc)
            limits = Limits.objects.get(
                client_id=self.question.client_id,
                start_date__lte=date_now,
                end_date__gte=date_now,
            )
            limits.question_limit -= 1
            limits.save()

        else:
            status = "error"

        BoostQuestion.objects.filter(id=self.question.id).update(
            status=status, account_id=self.account.id, sex=self.question.sex
        )
        return {"result": status}


class FavoriteReviewManager(WbClientAPI):
    def __init__(self, favorite_id):
        self.favorite_id = favorite_id

        self.wb_api = WbAPI()
        proxy_list = [
            "http://SdtHiE:QypQ4hraH8@46.8.57.150:3000",
            "http://SdtHiE:QypQ4hraH8@213.226.101.122:3000",
            "http://SdtHiE:QypQ4hraH8@188.130.187.159:3000",
            "http://SdtHiE:QypQ4hraH8@46.8.110.161:3000",
            "http://SdtHiE:QypQ4hraH8@46.8.14.233:3000",
            "http://SdtHiE:QypQ4hraH8@46.8.14.6:3000",
            "http://SdtHiE:QypQ4hraH8@212.115.49.222:3000",
            "http://SdtHiE:QypQ4hraH8@109.248.54.57:3000",
            "http://SdtHiE:QypQ4hraH8@46.8.110.221:3000",
            "http://SdtHiE:QypQ4hraH8@45.87.252.153:3000",
            "http://SdtHiE:QypQ4hraH8@46.8.193.170:3000",
            "http://SdtHiE:QypQ4hraH8@5.183.130.27:3000",
            "http://SdtHiE:QypQ4hraH8@45.87.252.128:3000",
            "http://SdtHiE:QypQ4hraH8@185.181.245.194:3000",
            "http://SdtHiE:QypQ4hraH8@185.181.244.58:3000",
            "http://SdtHiE:QypQ4hraH8@185.181.244.78:3000",
            "http://SdtHiE:QypQ4hraH8@194.32.229.177:3000",
            "http://SdtHiE:QypQ4hraH8@188.130.220.135:3000",
            "http://SdtHiE:QypQ4hraH8@46.8.107.32:3000",
            "http://SdtHiE:QypQ4hraH8@45.90.196.29:3000",
            "http://SdtHiE:QypQ4hraH8@95.182.125.71:3000",
        ]
        proxy_one = random.choice(proxy_list)
        proxy = {"http": proxy_one, "https": proxy_one}
        self.proxy = proxy
        # self.proxy = get_proxy()

        self.favorite = BoostLikeReview.objects.filter(id=self.favorite_id)[0]
        logger.debug(f"favorite is {self.favorite}")
        self.account = self.get_account()
        self.cookie = self.account.WILDAUTHNEW_V3
        self.rout_js_version = super().get_rout_js_version()
        logger.debug(f"account for favorite is {self.cookie}")

    def get_account(self):
        account_done = []
        favorites = BoostLikeReview.objects.filter(text=self.favorite.text)
        for favorite in favorites:
            account_done.append(favorite.account_id)
        account_all = (
            Account.objects.filter(status="free")
            .exclude(WILDAUTHNEW_V3__exact="")
            .exclude(WILDAUTHNEW_V3__isnull=True)
            .all()
        )
        for account in account_all:
            if account.id not in account_done:
                return account

    def get_max_skip(self, count_feedbacks):
        for i in range(0, 20):
            if count_feedbacks % 20 == 0:
                return count_feedbacks
            else:
                count_feedbacks += 1

    def add_favorite(self):
        nm = re.findall("(?<=catalog/).*?(?=/)", self.favorite.url)[0]
        response = self.wb_api.get_cards_detail(nm)
        imtId = response["data"]["products"][0]["root"]
        count_feedbacks = response["data"]["products"][0]["feedbacks"]
        max_skip = self.get_max_skip(count_feedbacks)
        print(imtId, count_feedbacks, max_skip)

        if self.favorite.action == "like":
            vote = 1
        elif self.favorite.action == "dislike":
            vote = -1
        else:
            raise Exception("error action")

        i = 0
        for count in range(0, max_skip, 20):
            print(i)
            i += 1
            data = {
                "imtId": imtId,
                "skip": count,
                "take": 20,
                "order": "dateDesc",
            }
            response = self.wb_api.get_reviews(data)
            for feedback in response["feedbacks"]:
                if self.favorite.id_sender == str(feedback["wbUserId"]):

                    data = {
                        "id": feedback["id"],
                        "vote": vote,
                        "link": feedback["imtId"],
                    }
                    response = super().add_favorite_review(data)

                    if response["resultState"] == 0:
                        status = "done"

                        date_now = datetime.now(d_timezone.utc)
                        limits = Limits.objects.get(
                            client_id=self.favorite.client_id,
                            start_date__lte=date_now,
                            end_date__gte=date_now,
                        )
                        limits.like_review_limit -= 1
                        limits.save()

                    else:
                        status = "error"
                        raise Exception("error to like review")

                    BoostLikeReview.objects.filter(id=self.favorite.id).update(
                        status=status,
                        account_id=self.account.id,
                    )
                    return response

        BoostLikeReview.objects.filter(id=self.favorite.id).update(
            status="error",
            account_id=self.account.id,
        )
        raise Exception("resultState not found")
