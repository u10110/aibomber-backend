# from dateutil.relativedelta import relativedelta
import datetime
import json

import requests

from .services.proxy import get_proxy, get_proxy_list


class X64ApiClient:
    """Get WB stock statistics."""

    def __init__(self, token):
        self.token = token
        self.base_url = "https://suppliers-stats.wildberries.ru/api/v1/supplier/"
        self.proxies = get_proxy_list()

    @staticmethod
    def connect(params, server):
        proxy = get_proxy()
        response = requests.get(url=server, params=params, proxies=proxy)
        return response

    def test(self):
        date_now = datetime.datetime.now()
        # dateFrom = (date_now - relativedelta(months=+3))
        dateFrom = date_now
        params = {"key": self.token, "dateFrom": dateFrom}
        for proxy in self.proxies:
            try:
                response = requests.get(
                    url=self.base_url + "stocks",
                    params=params,
                    proxies=proxy,
                    timeout=3,
                )
                if response.status_code == 200 or response.status_code == 400:
                    return response
                print(response)
            except:
                print("timeout")

        print(response)
        return response

    def get_ordered(self, url, week=False, flag=1, days=None):
        date = datetime.datetime.now()
        if week:
            dateFrom = date - datetime.timedelta(days=week * 7)
        elif days:
            dateFrom = date - datetime.timedelta(days=days)
        else:
            dateFrom = date
        params = {
            "dateFrom": dateFrom,
            "key": self.token,
            "flag": flag,
        }
        return (self.connect(params, self.base_url + url)).json()


class NewApiClient:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://suppliers-api.wildberries.ru/public/api/v1/info"
        self.proxies = get_proxy_list()

    @staticmethod
    def connect(params, server):
        proxy = get_proxy()
        response = requests.get(
            url=server, headers={"Authorization": self.token}, proxies=proxy
        )
        return response

    def test(self):
        for proxy in self.proxies:
            try:
                response = requests.get(
                    url=self.base_url,
                    headers={"Authorization": self.token},
                    proxies=proxy,
                    timeout=3,
                )
                print(response)
                if response.status_code == 200 or response.status_code == 401:
                    return response

            except:
                print("timeout")
        print(response)
        return response


class SuplierId:
    def __init__(
        self,
        token,
    ):
        self.supplier_id = token
        self.token = token
        self.proxy = get_proxy()
        print(self.proxy)

    @staticmethod
    def connect(params, server):
        proxy = get_proxy()
        response = requests.get(
            url=server, headers={"Authorization": self.token}, proxies=proxy
        )
        return response

    @classmethod
    def get_sku(self, resp_connect2):
        pass

    def test(self, resp_connect2):
        print(resp_connect2)
        response = json.loads(resp_connect2.content)
        sku = str(response[0]["nmId"])

        part = sku[: len(sku) - 3]
        vol = sku[: len(sku) - 5]

        for i in range(1, 9):
            self.base_url = (
                f"https://basket-0{i}.wb.ru/vol{vol}/part{part}/{sku}/info/sellers.json"
            )
            response = requests.get(
                url=self.base_url,
                headers={"Authorization": self.token},
                proxies=self.proxy,
            )
            if response.status_code == 200:
                break
        response = json.loads(response.content)
        print(response)
        if int(response["supplierId"]) == int(self.token):
            return True
        else:
            return False
