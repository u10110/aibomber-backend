import time
from urllib import response

import requests
import xmltodict

from . import services


class ZennoAPI:
    def __init__(self):
        self.login = "eramp.ru@yandex.ru"
        self.password = "916cde97a544b0392a5146505de0dce4"  # MD5
        self.url = "https://userarea.zennolab.com/BotStore.asmx/"
        self.body = f"login={self.login}&password={self.password}"
        self.headers = headers = {"Content-Type": "application/x-www-form-urlencoded"}

    def get_bot_list(self):
        url = f"{self.url}GetBotList"
        body = self.body
        time.sleep(2)
        response = requests.post(url, headers=self.headers, data=body)
        return response

    def get_current_custome_email(self, email):
        url = f"{self.url}GetCurrentCustomerEmail"
        body = f"{self.body}&customerEmail={email}"
        print(body)
        time.sleep(2)
        response = requests.post(url, headers=self.headers, data=body)
        print(response.text)
        response = xmltodict.parse(response.text)
        return response["string"]["#text"]

    def register_customer(self, email):
        url = f"{self.url}RegisterCustomer"
        body = f"{self.body}&email={email}&lang=ru"
        time.sleep(2)
        response = requests.post(url, headers=self.headers, data=body)
        print(response.text)
        response = xmltodict.parse(response.text)
        return response["string"]["#text"]

    def sale_bots(self, email, tariff, tariff_type):
        """автоматизация озон
        35714,35715
        OZON_LIKES_AND_DISLIKES 35715
        OZON_REVIEWS_AND_QUESTIONS 35714

        автоматизация вб
        35713,35712
        WB_LIKES_AND_DISLIKES 35713
        WB_REVIEWS_AND_QUESTIONS 35712

        Выкупы ОЗОН
        35707,35708,35709,35710,35711
        OZON_CHECKER 35711
        OZON_GEN_ACC 35710
        OZON_LIKE 35709
        OZON_OTZYW 35708
        OZON_POKUPKA 35707

        Выкупы ВБ
        35702,35703,35704,35705,35706
        WB_CHECKER 35706
        WB_GEN_ACC 35705
        WB_LIKE 35704
        WB_OTZYW 35703
        WB_POKUPKA 35702

        Поисковое продвиэение
        WB_NAKRUTKA_PF

        """

        url = f"{self.url}SaleBots"
        if tariff == "WILDBERRIES":
            if tariff_type == "buyouts":
                ids = "35702,35703,35704,35705,35706"
            elif tariff_type == "automation":
                ids = "35713,35712"
            elif tariff_type == "buyouts+automation":
                ids = "35702,35703,35704,35705,35706,35713,35712"

        elif tariff == "OZON":
            if tariff_type == "buyouts":
                ids = "35707,35708,35709,35710,35711"
            elif tariff_type == "automation":
                ids = "35714,35715"
            elif tariff_type == "buyouts+automation":
                ids = "35707,35708,35709,35710,35711,35714,35715"

        elif tariff == "WB+OZON":
            if tariff_type == "buyouts":
                ids = "35702,35703,35704,35705,35706,35707,35708,35709,35710,35711"
            elif tariff_type == "automation":
                ids = "35713,35712,35714,35715"
            elif tariff_type == "buyouts+automation":
                ids = "35702,35703,35704,35705,35706,35713,35712,35707,35708,35709,35710,35711,35714,35715"

        elif tariff == "search_promotion":
            ids = "37467"

        print(ids)
        body = f"{self.body}&customerEmail={email}&ids={ids}&isSubscription=true&subscriptionDaysCount=30&forProducts=1"
        print("before request")
        time.sleep(2)
        response = requests.post(url, headers=self.headers, data=body)
        print(response.text)
        return response

    def get_custome_box_link(self, email):
        url = f"{self.url}GetCustomerBoxLink"
        body = f"{self.body}&customerEmail={email}"
        print("before get_custome_box_link request")
        time.sleep(2)
        response = requests.post(url, headers=self.headers, data=body)
        print(response.text)
        print(response.status_code)
        if services.Eramp.isXml(response.text):
            response = xmltodict.parse(response.text)
            link_box = response["string"]["#text"]
            link_box = link_box.replace("v7.7", "v7.4")
            return link_box
        else:
            return False

    def change_subscription(self, tg_chat_id, email, sale_id, days):
        url = f"{self.url}ChangeSubscription"
        sale_id = int(sale_id)
        days = int(days)
        print(sale_id, days)
        body = f"{self.body}&saleId={sale_id}&addDays={days}"
        response = requests.post(url, headers=self.headers, data=body)
        print(response.text)
        return response
