import calendar
import datetime
import json
import random
import string

import requests
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from apps.billing.models import *
from apps.home.models import ClientSettings
from apps.home.services import amocrm

from .helper import Helper
from .models import *
from .robokassa import Robokassa


def checking_account(request):
    return render(request, "billing/bill2.html")


def check_promocode(request):
    if request.method == "POST":
        promocode = request.POST["promocode"]
        print(promocode.lower())
        if Promocode.objects.filter(promocode=promocode.lower()).exists():
            now = datetime.date.today()
            check_promocode = Promocode.objects.get(promocode=promocode.lower())
            past_used_promocodes = [
                i.promocode.id
                for i in Order.objects.filter(client=request.user)
                if i.promocode != None
            ]
            if check_promocode.id in past_used_promocodes:
                return JsonResponse({"resp": "used"}, status=200)
            elif check_promocode.expired_at < now:
                return JsonResponse({"resp": "expired"}, status=200)

            if check_promocode.type == "general":
                order = Order.objects.filter(
                    client=request.user, paid_status=False
                ).latest("created_at")
                if order.is_prolongation and not check_promocode.for_prolongation:
                    return JsonResponse({"resp": "no prolong"}, status=200)
                order.promocode = Promocode.objects.get(promocode=promocode.lower())
                order.price = order.price * (100 - check_promocode.discount) / 100
                order.save()
                Promocode.objects.filter(promocode=promocode.lower()).update(
                    used_times=check_promocode.used_times + 1
                )
                return JsonResponse({"resp": "ok"}, status=200)
            elif check_promocode.type == "unique":

                if (
                    check_promocode.expired_at >= now
                    and request.user.id == check_promocode.client_id
                ):
                    order = Order.objects.filter(
                        client=request.user, paid_status=False
                    ).latest("created_at")
                    if order.is_prolongation and not check_promocode.for_prolongation:
                        return JsonResponse({"resp": "no prolong"}, status=200)
                    order.promocode = Promocode.objects.get(promocode=promocode.lower())
                    order.price = order.price * (100 - check_promocode.discount) / 100
                    order.save()
                    Promocode.objects.filter(promocode=promocode.lower()).update(
                        used_times=check_promocode.used_times + 1
                    )
                    return JsonResponse({"resp": "ok"}, status=200)
                else:
                    print("expired")
                    return JsonResponse({"resp": "expired"}, status=200)
        else:
            return JsonResponse({"resp": "bad"}, status=200)


def generate_promocode():

    characters = string.ascii_lowercase + string.digits
    promocode = "".join(random.choice(characters) for i in range(6))
    return promocode


def create_promocode(request):

    if request.method == "POST":
        discount = 10
        expired_at = datetime.date.today() + datetime.timedelta(days=10)
        data = json.loads(request.body)
        tg_id = data["tg_id"]
        if "tg_id" in data:
            tg_id = data["tg_id"]
            client_settings = ClientSettings.objects.filter(tg_chat_id=tg_id).first()
            if not Promocode.objects.filter(
                client_id=client_settings.client_id
            ).exists():
                promocode = generate_promocode()
                Promocode.objects.create(
                    type="unique",
                    promocode=promocode,
                    expired_at=expired_at,
                    discount=discount,
                    client_id=client_settings.client_id,
                )
                return JsonResponse(
                    {
                        "result": {
                            "promocode": promocode,
                            "expired_at": expired_at,
                            "discount": discount,
                        }
                    },
                    status=200,
                )
            else:
                promocode = Promocode.objects.filter(
                    client_id=client_settings.client_id,
                )[0]
                return JsonResponse(
                    {
                        "result": {
                            "promocode": promocode.promocode,
                            "expired_at": promocode.expired_at,
                            "discount": promocode.discount,
                        }
                    },
                    status=200,
                )


def prolongation(request):
    context = {}
    tariff_list = ["showroom", "market", "hypermarket", "magigrand"]
    order = Order.objects.filter(
        client=request.user, paid_status=True, tariff__in=tariff_list
    )
    if not order:
        return render(request, "billing/prolongation.html", context=context)
    order = order.latest("created_at")
    if order:
        tariff = UnicTariff.objects.get(title=order.tariff)
        context["price"] = tariff.price_dict["1"]
    return render(request, "billing/prolongation.html", context=context)


def prolongation_order(request):
    if request.method == "POST":
        count_months = int(request.POST["period"])
        tariff_list = ["showroom", "market", "hypermarket", "magigrand"]
        order_old = Order.objects.filter(
            client=request.user, paid_status=True, tariff__in=tariff_list
        ).latest("created_at")
        tariff = UnicTariff.objects.get(title=order_old.tariff)
        price = tariff.price_dict["1"] * int(count_months)
        Order.objects.update_or_create(
            client=order_old.client,
            paid_status=False,
            defaults={
                "period_months": count_months,
                "tariff": order_old.tariff,
                "price": price,
                "is_prolongation": True,
                "prolongation_to": order_old.id,
            },
        )
        return JsonResponse({"link": "/prolongation-pay"}, status=200)


def prolongation_pay(request):
    context = {}
    tariff_list = ["showroom", "market", "hypermarket", "magigrand"]
    order = Order.objects.filter(
        client=request.user, paid_status=False, tariff__in=tariff_list
    ).latest("created_at")
    context["price"] = order.price
    return render(request, "billing/prolongation-order.html", context=context)


def prolongation_pay_link(request):
    if request.method == "POST":
        order = Order.objects.filter(client=request.user, paid_status=False).latest(
            "created_at"
        )
        if order.period_months == 1:
            month = " Месяц"
        elif order.period_months < 5:
            month = " Месяца"
        else:
            month = " Месяцев"
        url = Robokassa.generate_payment_link(
            order.price, order.id, order.tariff + " " + str(order.period_months) + month
        )
        return JsonResponse({"url": url}, status=200)


def create_order(request):
    if request.method == "POST":
        data = request.POST
        print(data)
        tariff = data["tariff"]
        period = data["period"]
        date_now = datetime.datetime.now(datetime.timezone.utc)

        if Order.objects.filter(client=request.user, paid_status=False).exists():
            old_records = Order.objects.filter(client=request.user, paid_status=False)
            old_records.delete()
        if Order.objects.filter(client=request.user, paid_status=True).exists():
            paid_order = Paid.objects.filter(client=request.user).latest("end_date")
            print(paid_order.end_date >= date_now.date())
            print(
                paid_order.order.tariff
                in ["showroom", "market", "hypermarket", "magigrand"]
            )
            print(tariff != "custom")
            if (
                paid_order.end_date >= date_now.date()
                and paid_order.order.tariff
                in ["showroom", "market", "hypermarket", "magigrand"]
            ) and tariff != "custom":
                # return HttpResponseRedirect("/bill/")
                return JsonResponse({"link": "/personal-room/#tariff"}, status=200)

        if tariff and period:
            if tariff == "custom":
                print(data)
                price = Helper.validate_calculator(data)
                print(price)
                if price != int(data["result"]):
                    return False
                tariff_obj = TariffCalculated.objects.create(
                    client=request.user,
                    buyout_limit=data["redemptions"],
                    review_limit=data["reviews"],
                    like_limit=data["likes"],
                    question_limit=data["questions"],
                    like_review_limit=data["likes-on-reviews"],
                    search_promotion=data["search_promotion"]
                    if "search_promotion" in data
                    else 0,
                    monitor=data["monitor"],
                    monitoring_kz=data["monitoring_kz"]
                    if "monitoring_kz" in data
                    else 0,
                    adv_company=data["adv_company"] if "adv_company" in data else 0,
                    monitoring_rate=data["rate-monitoring"]
                    if "rate-monitoring" in data
                    else 0,
                    course_autobuy=data["course"] if "course" in data else 0,
                    price=data["result"],
                )
                order = Order.objects.create(
                    client=request.user,
                    tariff=tariff,
                    period_months=period,
                    paid_status=False,
                    is_calculated=True,
                    calculated_tariff=tariff_obj,
                    price=data["result"],
                )
            else:
                tariff = UnicTariff.objects.get(title=tariff)
                order = Order.objects.create(
                    client=request.user,
                    tariff=tariff,
                    period_months=period,
                    paid_status=False,
                    price=tariff.price_dict[period],
                )
        if Order.objects.filter(client=request.user, paid_status=True).exists():
            paid_order = Paid.objects.filter(client=request.user).latest("end_date")
            if paid_order.end_date >= date_now.date() and tariff == "custom":
                # return HttpResponseRedirect('/prolonagation-calculated/')
                return HttpResponseRedirect("/bill?prolonagation_calculated=1")
                # return JsonResponse({"link": "/bill?prolonagation_calculated=1"}, status=200)
            elif (
                paid_order.end_date >= date_now.date()
                and paid_order.order.tariff
                not in ["showroom", "market", "hypermarket", "magigrand"]
            ):
                # return HttpResponseRedirect('/bill?from_test=1')
                return JsonResponse({"link": "/bill?from_test=1"}, status=200)
            elif paid_order.end_date <= date_now.date() and tariff == "custom":
                return HttpResponseRedirect("/bill/")

        elif (
            Order.objects.filter(client=request.user, paid_status=False).exists()
            and tariff != "custom"
        ):
            return JsonResponse({"link": "/bill/"}, status=200)
        # return HttpResponseRedirect('/bill/')
        elif (
            Order.objects.filter(client=request.user, paid_status=False).exists()
            and tariff == "custom"
        ):
            return HttpResponseRedirect("/bill/")
        return JsonResponse({"link": "/bill/"}, status=200)

    # return JsonResponse({"respond": "ok"}, status=200)
    return JsonResponse({"link": "/bill/"}, status=200)


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def bill_ok(request):
    params = dict(request.GET)
    context = {}
    for k, v in params.items():
        params[k] = v[0]
    if Robokassa.check_success_payment(request=params):
        # if True:
        try:

            date_now = datetime.datetime.now(datetime.timezone.utc)
            paid = Paid.objects.filter(client=request.user).latest("end_date")
            if paid.end_date >= date_now.date():
                order_old = Order.objects.filter(
                    client=request.user, paid_status=True
                ).latest("created_at")
                order = Order.objects.filter(
                    client=request.user, paid_status=False
                ).latest("created_at")
                if order.is_calculated == True:
                    limits = Limits.objects.get(
                        client=request.user,
                        start_date__lte=date_now,
                        end_date__gte=date_now,
                    )
                    limits.buyout_limit += order.calculated_tariff.buyout_limit
                    limits.review_limit += order.calculated_tariff.review_limit
                    limits.like_limit += order.calculated_tariff.like_limit
                    limits.question_limit += order.calculated_tariff.question_limit
                    limits.like_review_limit += (
                        order.calculated_tariff.like_review_limit
                    )
                    limits.save()
                    order.paid_status = True
                    order.is_prolongation = True
                    while order_old.is_prolongation:
                        order_old = Order.objects.get(id=order_old.prolongation_to)
                    order.prolongation_to = order_old.id
                    order.save()
                    context["error"] = False
                    # return render(request, "billing/order.html", context)
                    return HttpResponseRedirect("/personal-room/")
                elif order_old.tariff not in [
                    "showroom",
                    "market",
                    "hypermarket",
                    "magigrand",
                    "custom",
                ] and order.tariff in [
                    "showroom",
                    "market",
                    "hypermarket",
                    "magigrand",
                ]:
                    order.paid_status = True
                    order.save()
                    start_date = datetime.datetime.now(datetime.timezone.utc)
                    end_date = add_months(start_date, order.period_months)
                    paid = Paid.objects.create(
                        client=request.user,
                        order=order,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    start_period = start_date

                    paid_old = Paid.objects.get(order=order_old)
                    limit = Limits.objects.get(paid_info=paid_old)
                    paid_old.end_date = paid_old.start_date
                    limit.end_date = limit.start_date
                    paid_old.save()
                    limit.save()

                else:
                    order.paid_status = True
                    order.is_prolongation = True
                    order.save()
                    # paid = Paid.objects.filter(order=order_old)
                    end_date = add_months(paid.end_date, order.period_months)
                    start_period = paid.end_date
                    paid.order = order
                    paid.end_date = end_date
                    paid.save()
            else:
                order = Order.objects.get(client=request.user, paid_status=False)
                order.paid_status = True
                order.save()
                start_date = datetime.datetime.now(datetime.timezone.utc)
                end_date = add_months(start_date, order.period_months)
                paid = Paid.objects.create(
                    client=request.user,
                    order=order,
                    start_date=start_date,
                    end_date=end_date,
                )
                start_period = start_date

                order_check = Order.objects.filter(client=request.user)
                if order_check and order_check.latest("created_at").is_prolongation:
                    print("request to amo pay")
                    r = requests.post(
                        "https://eliment.ai/amotest/",
                        json={
                            "client_id": request.user.id,
                            "type_deal": "pay",
                        },
                        timeout=10,
                    )
                    if r.status_code == 200:
                        print(f"amo {r.text}")
                elif len(order_check) == 1:
                    print("request to amo pay_first")
                    r = requests.post(
                        "https://eliment.ai/amotest/",
                        json={
                            "client_id": request.user.id,
                            "type_deal": "pay_first",
                        },
                        timeout=10,
                    )
                    if r.status_code == 200:
                        print(f"amo {r.text}")
                else:
                    # TODO: это и не продление и не первая покупка (заменить)
                    print("request to amo pay")
                    r = requests.post(
                        "https://eliment.ai/amotest/",
                        json={"client_id": request.user.id, "type_deal": "pay"},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        print(f"amo {r.text}")

        except Exception as e:
            print(e)
            order = Order.objects.get(client=request.user, paid_status=False)
            order.paid_status = True
            order.save()
            start_date = datetime.datetime.now(datetime.timezone.utc)
            end_date = add_months(start_date, order.period_months)
            paid = Paid.objects.create(
                client=request.user,
                order=order,
                start_date=start_date,
                end_date=end_date,
            )
            start_period = start_date
        if order.is_calculated == True:
            limits = order.calculated_tariff
        else:
            limits = UnicTariff.objects.get(title=order.tariff)
        tariff = [
            limits.buyout_limit,
            limits.review_limit,
            limits.like_limit,
            limits.like_review_limit,
            limits.question_limit,
        ]
        not_first = False
        for month in range(1, order.period_months + 1):
            end_period = add_months(start_period, 1)
            Limits.objects.create(
                client=request.user,
                buyout_limit=tariff[0],
                review_limit=tariff[1],
                like_limit=tariff[2],
                like_review_limit=tariff[3],
                question_limit=tariff[4],
                paid_info=paid,
                order=order,
                start_date=start_period + datetime.timedelta(days=1)
                if not_first
                else start_period,
                end_date=end_period,
            )
            start_period = end_period
            not_first = True
        context["error"] = False

        order_check = Order.objects.filter(client=request.user)
        if order_check and order_check.latest("created_at").is_prolongation:
            print("request to amo pay")
            r = requests.post(
                "https://eliment.ai/amotest/",
                json={
                    "client_id": request.user.id,
                    "type_deal": "pay",
                },
                timeout=10,
            )
            if r.status_code == 200:
                print(f"amo {r.text}")
        elif len(order_check) == 1:
            print("request to amo pay_first")
            r = requests.post(
                "https://eliment.ai/amotest/",
                json={"client_id": request.user.id, "type_deal": "pay_first"},
                timeout=10,
            )
            if r.status_code == 200:
                print(f"amo {r.text}")
        else:
            # TODO: это и не продление и не первая покупка (заменить)
            print("request to amo pay")
            r = requests.post(
                "https://eliment.ai/amotest/",
                json={"client_id": request.user.id, "type_deal": "pay"},
                timeout=10,
            )
            if r.status_code == 200:
                print(f"amo {r.text}")
        # return render(request, "billing/order.html", context)
        return HttpResponseRedirect("/personal-room/")


def bill_bad(request):
    if Order.objects.filter(client=request.user, paid_status=False).exists():

        order_check = Order.objects.filter(client=request.user)

        if order_check and order_check.latest("created_at").is_prolongation:
            print("request to amo pay")
            r = requests.post(
                "https://eliment.ai/amotest/",
                json={"client_id": request.user.id, "type_deal": "unscc_pay"},
                timeout=10,
            )
            if r.status_code == 200:
                print(f"amo {r.text}")

        elif len(order_check) == 1:
            print("request to amo pay_first")
            r = requests.post(
                "https://eliment.ai/amotest/",
                json={"client_id": request.user.id, "type_deal": "unscc_pay_first"},
                timeout=10,
            )
            if r.status_code == 200:
                print(f"amo {r.text}")

        else:
            # TODO: это и не продление и не первая покупка (заменить)
            print("request to amo unscc_pay")
            r = requests.post(
                "https://eliment.ai/amotest/",
                json={"client_id": request.user.id, "type_deal": "unscc_pay"},
                timeout=10,
            )
            if r.status_code == 200:
                print(f"amo {r.text}")

        order = Order.objects.get(client=request.user, paid_status=False)

        if order.period_months == 1:
            period = "1 месяц"
        elif order.period_months == 3:
            period = "3 месяца"
        elif order.period_months == 6:
            period = "6 месяцев"
        elif order.period_months == 12:
            period = "12 месяцев"

        if order.tariff == "showroom":
            tariff = "Шоурум"
        elif order.tariff == "market":
            tariff = "Магазин"
        elif order.tariff == "hypermarket":
            tariff = "Гипермаркет"
        elif order.tariff == "magigrand":
            tariff = "magigrand"

        context = {
            "have_subscribe": False,
            "period": period,
            "tariff": tariff,
            "price": order.price,
        }
        context["error"] = True
        context["error_message"] = "Оплата не прошла"
        return render(request, "billing/order.html", context)


def pay_buyout(request):
    if request.method == "POST":
        try:
            count_months = int(request.POST["count_month"])
            tariff_list = ["showroom", "market", "hypermarket", "magigrand", "custom"]
            order_old = Order.objects.filter(
                client=request.user, paid_status=True, tariff__in=tariff_list
            ).latest("created_at")
            if order_old.tariff == "custom":
                price = order_old.calculated_tariff.price * int(count_months)
                Order.objects.update_or_create(
                    client=order_old.client,
                    paid_status=False,
                    defaults={
                        "is_calculated": True,
                        "calculated_tariff": order_old.calculated_tariff,
                        "period_months": count_months,
                        "tariff": order_old.tariff,
                        "price": price,
                    },
                )
            else:
                tariff = UnicTariff.objects.get(title=order_old.tariff)
                price = tariff.price_dict["1"] * int(count_months)
                Order.objects.update_or_create(
                    client=order_old.client,
                    paid_status=False,
                    defaults={
                        "period_months": count_months,
                        "tariff": order_old.tariff,
                        "price": price,
                        "is_prolongation": True,
                        "prolongation_to": order_old.id,
                    },
                )
            order_new = Order.objects.filter(client=order_old.client).latest(
                "created_at"
            )
            url = Robokassa.generate_payment_link(
                price, order_new.id, order_old.tariff + " " + str(count_months)
            )
            return JsonResponse({"url": url}, status=200)
        except Exception as e:
            print(e)
            print("no prolongation")
        if Order.objects.filter(client=request.user, paid_status=False).exists():
            order = Order.objects.get(client=request.user, paid_status=False)

            if order.period_months == 1:
                period = "1 месяц"
            elif order.period_months == 3:
                period = "3 месяца"
            elif order.period_months == 6:
                period = "6 месяцев"
            elif order.period_months == 12:
                period = "12 месяцев"

            url = Robokassa.generate_payment_link(
                order.price, order.id, order.tariff + " " + period
            )
            return JsonResponse({"url": url}, status=200)
    elif request.method == "GET":
        print(Paid.objects.filter(client=request.user))
        date_now = datetime.datetime.now(datetime.timezone.utc)
        if Paid.objects.filter(client=request.user).exists():
            if (
                Paid.objects.filter(client=request.user).latest("end_date").end_date
                >= date_now.date()
                and request.GET.get("prolonagation_calculated", 0) != "1"
            ) and (
                (
                    Paid.objects.filter(client=request.user).latest("end_date").end_date
                    >= date_now.date()
                    and request.GET.get("from_test", 0) != "1"
                )
            ):
                limits = Limits.objects.get(
                    client=request.user,
                    start_date__lte=date_now,
                    end_date__gte=date_now,
                )
                if limits.paid_info.order.is_calculated == True:
                    tariff = "Собственный"
                else:
                    tariff = limits.paid_info.order.tariff
                end_date = limits.paid_info.end_date
                limit_end_date = limits.end_date
                if tariff == "showroom":
                    tariff = "Шоурум"
                elif tariff == "market":
                    tariff = "Магазин"
                elif tariff == "hypermarket":
                    tariff = "Гипермаркет"
                elif tariff == "magigrand":
                    tariff = "Магигранд"
                context = {
                    "have_subscribe": True,
                    "limits": limits,
                    "tariff": tariff,
                    "end_date": end_date,
                    "limit_end_date": limit_end_date,
                }
                return render(request, "billing/order.html", context)
        if Order.objects.filter(client=request.user, paid_status=False).exists():

            order = Order.objects.get(client=request.user, paid_status=False)

            if order.period_months == 1:
                period = "1 месяц"
            elif order.period_months == 3:
                period = "3 месяца"
            elif order.period_months == 6:
                period = "6 месяцев"
            elif order.period_months == 12:
                period = "12 месяцев"

            if order.is_calculated == True:
                tariff = "Собственный"
            elif order.tariff == "showroom":
                tariff = "Шоурум"
            elif order.tariff == "market":
                tariff = "Магазин"
            elif order.tariff == "hypermarket":
                tariff = "Гипермаркет"
            elif order.tariff == "magigrand":
                tariff = "Магигранд"

            context = {
                "have_subscribe": False,
                "period": period,
                "tariff": tariff,
                "price": order.price,
            }
            return render(request, "billing/order.html", context)

        return HttpResponseRedirect("/pricing/")
