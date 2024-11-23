import json
from tabnanny import check

import requests
from django.shortcuts import render
from django.urls import reverse
from requests import request

from apps.alert.views import advertising_rate
from apps.billing.models import Order
from apps.billing.helper import Helper as BHelper
from apps.home.helper import Helper

from .forms import *


def advertising(request):
    return render(request, "marketing/advertising.html")


def in_tariff(request):
    order = Order.objects.filter(client_id=request.user.id).latest("tariff")
    if (
        order.tariff == "market"
        or order.tariff == "hypermarket"
        or order.tariff == "magigrand"
    ):
        return True
    else:
        return False


def actual_bids(request):
    print(request)
    if request.method == "POST":
        context = {}
        form = ActualBidsForm(request.POST)
        if form.is_valid():
            if BHelper(request.user.id).get_max_limit('monitoring_rate') is False:
                context["error"] = True
                context[
                    "error_message"
                ] = "В выбранный вами тариф не входит работа с ставками"
                return render(request, "marketing/actual-bids.html", context)
            url = request.build_absolute_uri(reverse("advertising_rate"))
            host = request.META["HTTP_HOST"]
            if host == "app.mplab.io":
                url = url.replace("http://", "https://")
            print("url---------", url)
            r = requests.post(
                url,
                data={
                    "key_phrase": form.cleaned_data.get("to_search"),
                    "type_ad": form.cleaned_data.get("type_advertise"),
                },
            )
            print(r.text)
            data = r.json()
            if data != "not found":
                page1 = []
                page2 = []
                context["error"] = False
                for item in data:
                    if item["page"] == 1:
                        page1.append(item)
                    elif item["page"] == 2:
                        page2.append(item)
                context["page1"] = page1
                context["page2"] = page2
            else:
                context["error"] = True
                context[
                    "error_message"
                ] = "По данному ключевому запросу никто не рекламируется"

        else:
            context["error"] = True
            context["error_message"] = "Неправильно введены данные"
        return render(request, "marketing/actual-bids.html", context)
    return render(request, "marketing/actual-bids.html")
