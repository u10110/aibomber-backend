import json
import re

import requests
from decouple import config
from apps.home.models import AmoCrm

AMOCRM_URI = config("AMOCRM_URI")


class Contact:
    def __init__(self):
        pass


class Deal:
    def __init__(self, phone, pipeline_id, status_id, source, name):
        self.phone = re.sub("[^0-9]", "", phone)
        self.pipeline_id = pipeline_id
        self.status_id = status_id
        self.name = name
        self.amo = AmoCrm.objects.get(id=1)

        if source == "website":
            self.headers = self.login_crm_website()
        elif source == "tg":
            self.headers = self.login_crm_tg()

    def login_crm_website(self):

        data = {
            "client_id": "a35f023e-33ed-4d03-b951-1b14eef49a1e",
            "client_secret": "2Uh5f7oThcQ8AtOYCc4NU2KxJo0qqBp6Zq0q65C8tOUHuoOYaJTP5DDmZCD6H6WJ",
            "grant_type": "refresh_token",
            "refresh_token": self.amo.website["refresh_token"],
            "redirect_uri": "https://app.mplab.io/"
        }

        url = 'https://mplabio.amocrm.ru/oauth2/access_token'
        r = requests.post(url, data=data)
        headers = {
            "authorization": 'Bearer ' + r.json()['access_token']
        }
        self.amo.website = r.json()
        self.amo.save()
        return headers

    def login_crm_tg(self):
        data = {
            "client_id": "c2ee80a7-cfbd-4d6a-b8a4-9f1b61514bbb",
            "client_secret": "hypFpnGHcX9b3QWaPdoQlOEH55l4Zlxvk1xHMJiooqU0OZ2Dr9w7oY8iehk0yBEX",
            "grant_type": "refresh_token",
            "refresh_token": self.amo.tg["refresh_token"],
            "redirect_uri": "https://app.mplab.io/"
        }

        url = 'https://mplabio.amocrm.ru/oauth2/access_token'
        r = requests.post(url, data=data)
        headers = {
            "authorization": 'Bearer ' + r.json()['access_token']
        }
        self.amo.tg = r.json()
        self.amo.save()
        return headers

    def first_registration(self):
        data = [
            {
                "name": self.name,
                "pipeline_id": self.pipeline_id,
                "status_id": self.status_id,
                "responsible_user_id": 8412946,
                "_embedded": {
                    "contacts": [
                        {
                            "responsible_user_id": 8412946,
                            "custom_fields_values": [
                                {
                                    "field_id": 604529,
                                    "values": [
                                        {
                                            "value": self.phone,
                                            "enum_id": 384317,
                                            "enum_code": "WORK",
                                        }
                                    ],
                                }
                            ]
                        }
                    ]
                },
            }
        ]
        url = f"{AMOCRM_URI}api/v4/leads/complex"

        response = requests.post(url, headers=self.headers, json=data)
        print(response.json())

    def redact_deal(self):
        account_id, deal_id = self.get_deal_id()
        if not deal_id:
            print('Не найдена сделка')
            return False
        url = f"{AMOCRM_URI}api/v4/leads/{deal_id}"
        data = {
            "custom_fields_values": [
                {
                    "field_id": 624659,
                    "values": [
                        {
                            "value": True
                        }
                    ]
                },
                {
                    "field_id": 627741,
                    "values": [
                        {
                            "value": True
                        }
                    ]
                }
            ]
        }
        response = requests.patch(url, headers=self.headers, json=data)
        print(response.json())

    def get_deal_id(self):
        account_id = self.get_contact()
        if not account_id:
            return False, False
        print(account_id)
        url = f"{AMOCRM_URI}api/v4/leads?limit=250&query=Новая регистрация&with=contacts"
        response = requests.get(url, headers=self.headers)
        response = json.loads(response.content)
        # print(response)
        for l in response["_embedded"]["leads"]:
            if l['_embedded']['contacts'][0]['id'] == account_id:
                return False, l['id']
        return account_id, False

    def get_contact(self):
        url = f"{AMOCRM_URI}api/v4/contacts?query={self.phone}"
        # print(self.headers)
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return False
        response = json.loads(response.content)

        for c in response["_embedded"]["contacts"]:
            for cc in c["custom_fields_values"]:
                for ccc in cc["values"]:
                    if ccc["value"] == self.phone:
                        return c["id"]
        return False

    def create_payed_deal(self, price):
        data = [
            {
                "name": self.name,
                "pipeline_id": self.pipeline_id,
                "status_id": self.status_id,
                "responsible_user_id": 8412946,
                "price": price,
                "_embedded": {
                    "contacts": [
                        {
                            "responsible_user_id": 8412946,
                            "custom_fields_values": [
                                {
                                    "field_id": 604529,
                                    "values": [
                                        {
                                            "value": self.phone,
                                            "enum_id": 384317,
                                            "enum_code": "WORK",
                                        }
                                    ],
                                }
                            ]
                        }
                    ]
                },
            }
        ]
        url = f"{AMOCRM_URI}api/v4/leads/complex"

        response = requests.post(url, headers=self.headers, json=data)
        print(response.json())

    def payed_deal(self, price):
        account_id, deal_id = self.get_deal_id()
        if not deal_id:
            self.create_payed_deal(price)
            return
        url = f"{AMOCRM_URI}api/v4/leads/{deal_id}"
        data = {
            "status_id": 142,
            "price": price,
            "responsible_user_id": 8412946
        }
        response = requests.patch(url, headers=self.headers, json=data)
        print(response.json())
