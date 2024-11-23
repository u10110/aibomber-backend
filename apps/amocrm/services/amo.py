import json
from abc import ABC, abstractmethod

import requests

from apps.authentication.models import User, UserInfo
from apps.billing.models import Limits, Order, Paid, UnicTariff


class Deal:
    def __init__(self, client_id, type_deal):
        self.client_id = client_id
        self.type_deal = type_deal
        self.client = User.objects.get(id=client_id)
        self.client_info = (
            UserInfo.objects.get(user_id=client_id)
            if UserInfo.objects.filter(user_id=client_id).exists()
            else None
        )

        if not Order.objects.filter(client_id=client_id).exists():
            self.paid_count = None
            self.order_first = None
            self.order_last = None
            self.paid_first = None
            self.paid_last = None
            self.limits_first = None
            self.limits_last = None
        else:

            self.paid_count = (
                Order.objects.filter(client_id=client_id).filter(paid_status=True)
            ).count()
            self.order_first = (
                Order.objects.filter(client_id=client_id).select_related("promocode")
            )[0]
            self.order_last = (
                Order.objects.filter(client_id=client_id).select_related("promocode")
            ).latest("id")

            if Paid.objects.filter(order_id=self.order_first.id).exists():
                self.paid_first = Paid.objects.filter(
                    order_id=self.order_first.id
                ).get()
            else:
                self.paid_first = None

            if Paid.objects.filter(order_id=self.order_last.id).exists():
                self.paid_last = Paid.objects.filter(order_id=self.order_last.id).get()
            else:
                self.paid_last = None

            if Limits.objects.filter(order_id=self.order_first.id).exists():
                self.limits_first = Limits.objects.filter(
                    order_id=self.order_first.id
                ).get()
            else:
                self.limits_first = None

            if Limits.objects.filter(order_id=self.order_last.id).exists():
                self.limits_last = Limits.objects.filter(
                    order_id=self.order_last.id
                ).get()
            else:
                self.limits_last = None

    def get_formet_limits(self, is_first_order):
        if self.limits_first or self.limits_last:
            if is_first_order:
                limits = self.limits_first
            else:
                limits = self.limits_last
        else:
            return None
        return f"выкупы {limits.buyout_limit}\/n\/отзывы {limits.review_limit}\/n\/лайки {limits.like_limit}\/n\/лайки на отзывы {limits.like_review_limit}\/n\/вопросы {limits.question_limit}\/n\/"

    def registrate(self):
        """Регистрация"""
        data = {
            "client": "mplabio",
            "type": "register_lt",
            "phone": self.client.phone,
        }

        return data

    def registrate_test(self):
        """Регистрация пробного периода"""
        data = {
            "client": "mplabio",
            "type": "register",
            "phone": self.client.phone,
            "rek_source": self.order_first.tariff if self.order_first else None,
            "tariff_name": self.order_first.tariff if self.order_first else None,
            "tariff_time": self.order_first.period_months if self.order_first else None,
            "date_begin": self.paid_first.start_date.strftime("%Y-%m-%d")
            if self.paid_first
            else None,
            "date_end": self.paid_first.end_date.strftime("%Y-%m-%d")
            if self.paid_first
            else None,
            "limit_str": self.get_formet_limits(is_first_order=True),
        }

        return data

    def prolongation_of_test(self):
        """Продления пробного периода"""
        data = {
            "client": "mplabio",
            "type": "prolong",
            "phone": self.client.phone,
            "rek_source": self.order_first.tariff,
            "tariff_name": self.order_first.tariff,
            "tariff_time": self.order_first.period_months,
            "date_begin": self.paid_first.start_date.strftime("%Y-%m-%d")
            if self.paid_first
            else None,
            "date_end": self.paid_first.end_date.strftime("%Y-%m-%d")
            if self.paid_first
            else None,
            "limit_str": self.get_formet_limits(is_first_order=True),
        }

        return data

    def pay_failure_first(self):
        """
        Неуспешная ПЕРВАЯ покупка платного тарифа (order без pay) - попытка оплаты
        """
        data = {
            "client": "mplabio",
            "type": "unscc_pay_first",
            "phone": self.client.phone,
            "promocode": self.order_first.promocode.promocode
            if self.order_first.promocode
            else None,
            "tariff_name": self.order_first.tariff,
            "tariff_cost": self.order_first.price,  # TODO add COST OF TARIFF BY MONTH
            "tariff_time": self.order_first.period_months,
            "tariff_add": None,  # TODO if custom
            "tariff_time_add": None,  # TODO if custom
            "date_begin": self.paid_first.start_date.strftime("%Y-%m-%d")
            if self.paid_first
            else None,
            "date_end": self.paid_first.end_date.strftime("%Y-%m-%d")
            if self.paid_first
            else None,
            "summ": self.order_first.price,
            "limit_str": self.get_formet_limits(is_first_order=True),
        }

        return data

    def pay_failure_repeat(self):
        """
        Неуспешная ПОВТОРНАЯ(если уже была хотя бы 1 успешная) покупка платного тарифа (order без pay) - попытка оплаты
        """
        data = {
            "client": "mplabio",
            "type": "unscc_pay",
            "phone": self.client.phone,
            "promocode": self.order_last.promocode.promocode
            if self.order_last.promocode
            else None,
            "tariff_name": self.order_last.tariff,
            "tariff_cost": self.order_last.price,  # TODO add COST OF TARIFF BY MONTH
            "tariff_time": self.order_last.period_months,
            "tariff_add": None,
            "tariff_time_add": None,
            "date_begin": self.paid_last.start_date.strftime("%Y-%m-%d")
            if self.paid_last
            else None,
            "date_end": self.paid_last.end_date.strftime("%Y-%m-%d")
            if self.paid_last
            else None,
            "summ": self.order_first.price,
            "limit_str": self.get_formet_limits(is_first_order=False),
        }

        return data

    def pay_success_first(self):
        """
        Успешная ПЕРВАЯ покупка платного тарифа (order + pay)
        """
        data = {
            "client": "mplabio",
            "type": "pay_first",
            "phone": self.client.phone,
            "paid_count": self.paid_count,
            # "use_count": "",
            "promocode": self.order_first.promocode.promocode
            if self.order_first.promocode
            else None,
            "tariff_name": self.order_first.tariff,
            "tariff_cost": self.order_first.price,  # TODO add COST OF TARIFF BY MONTH
            "tariff_time": self.order_first.period_months,
            "tariff_add": None,
            "tariff_time_add": None,
            "date_begin": self.paid_first.start_date.strftime("%Y-%m-%d")
            if self.paid_first
            else None,
            "date_end": self.paid_first.end_date.strftime("%Y-%m-%d")
            if self.paid_first
            else None,
            "summ": self.order_first.price,
            "limit_str": self.get_formet_limits(is_first_order=True),
        }

        return data

    def pay_success_repeat(self):
        """
        Успешная ПОВТОРНАЯ покупка платного тарифа (order + pay)
        """
        data = {
            "client": "mplabio",
            "type": "pay",
            "phone": self.client.phone,
            "paid_count": self.paid_count,
            # "use_count": "",
            "promocode": "",
            "tariff_name": self.order_last.tariff,
            "tariff_cost": self.order_last.price,  # TODO add COST OF TARIFF BY MONTH
            "tariff_time": self.order_last.period_months,
            "tariff_add": None,
            "tariff_time_add": None,
            "date_begin": self.paid_last.start_date.strftime("%Y-%m-%d")
            if self.paid_last
            else None,
            "date_end": self.paid_last.end_date.strftime("%Y-%m-%d")
            if self.paid_last
            else None,
            "summ": self.order_first.price,
            "limit_str": self.get_formet_limits(is_first_order=False),
        }

        return data

    def date_end_change(self):
        """Изменение даты окончания платного или пробного тарифа"""
        data = {
            "client": "mplabio",
            "type": "date_ch",
            "phone": self.client.phone,
            "use_count": self.order_last.period_months,
            "tariff_name": self.order_last.tariff,
            "date_end": self.paid_last.end_date.strftime("%Y-%m-%d")
            if self.paid_last
            else None,
            "limit_str": self.get_formet_limits(is_first_order=False),
        }

        return data

    def limits_exhausted(self):
        """
        Досрочное истечение лимитов по тарифу (скоро истечет, менее 10% от месячного лимита)
        ВНИМАНИЕ , для пробных периодов не передаем
        """
        data = {
            "client": "mplabio",
            "type": "limit_end",
            "phone": self.client.phone,
            "limit_end": None,
            "tariff_name": self.order_last.tariff,
            "limit_str": self.get_formet_limits(is_first_order=False),
        }

        return data

    def profile_change(self):
        """Передача данных пользователя"""
        data = {
            "client": "mplabio",
            "type": "user_d_add",
            "phone": self.client.phone,
            "name": (
                f"{self.client.first_name} {self.client.last_name}"
                if self.client.first_name or self.client.last_name
                else ""
            ),
            "mail": self.client.email,
            "sex": self.client_info.sex if self.client_info else None,
            "birth": self.client_info.date_birthday.strftime("%Y-%m-%d")
            if self.client_info.date_birthday
            else None
            if self.client_info
            else None,
        }
        return data

    def save(self):
        if self.type_deal == "register_lt":
            data = self.registrate()
        if self.type_deal == "register":
            data = self.registrate_test()
        elif self.type_deal == "unscc_pay_first":
            data = self.pay_failure_first()
        elif self.type_deal == "unscc_pay":
            data = self.pay_failure_repeat()
        elif self.type_deal == "pay_first":
            data = self.pay_success_first()
        elif self.type_deal == "pay":
            data = self.pay_success_repeat()
        elif self.type_deal == "date_ch":
            data = self.date_end_change()
        elif self.type_deal == "limit_end":
            data = self.limits_exhausted()
        elif self.type_deal == "user_d_add":
            data = self.profile_change()

        print(data)
        url = "https://wdg.biz-crm.ru/inserv/in.php"
        headers = {"Content-Type": "application/json; charset=utf-8'"}
        response = requests.post(
            url,
            headers=headers,
            json=data,
        )
        print(json.dumps(data, indent=4, sort_keys=True, default=str))
        print(response.status_code)
        if response.status_code != 200:
            raise "AMO WEBSERVER DONT RESPONSE, FIX IT"
        else:
            pass
        return data
