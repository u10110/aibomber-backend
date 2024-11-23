import datetime
import json
from http import client

from django.db.models import Count, Q, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from apps.billing.models import Limits, Order
from apps.home.models import *
from apps.home.WB_token import NewApiClient, SuplierId, X64ApiClient

from .forms import *
from .models import *


@csrf_exempt
def add_suppliers_api(request):
    if request.method == "POST":
        data = request.POST

        if Client_Supplier_Access.objects.filter(
            client_settings=ClientSettings.objects.get(client=request.user)
        ).exists():
            current_settings = Client_Supplier_Access.objects.get(
                client_settings=ClientSettings.objects.get(client=request.user)
            )
        else:
            current_settings = Client_Supplier_Access.objects.create(
                api_token_64=None,
                api_token_new=None,
                supplier_id=None,
                client_settings=ClientSettings.objects.get(client=request.user),
            )
        print("current_settings: %s" % current_settings)

        # if current_settings.exists():
        if current_settings:
            # current_settings = current_settings[0]
            old_api_token_64 = current_settings.api_token_64
            old_api_token_new = current_settings.api_token_new
            old_supplier_id = current_settings.supplier_id
        else:
            old_api_token_64 = None
            old_api_token_new = None
            old_supplier_id = None

        resp_connect = X64ApiClient(data["apix64"]).test()
        if resp_connect.status_code == 200 and data["apix64"] != old_api_token_64:
            current_settings.api_token_64 = data["apix64"]
        elif resp_connect.status_code != 200:
            print({"resp": "bad_apix64"})
            return JsonResponse({"resp": "bad_apix64"}, status=200)
        resp_connect2 = NewApiClient(data["new-token"]).test()
        if resp_connect2.status_code == 200 and data["new-token"] != old_api_token_new:
            current_settings.api_token_new = data["new-token"]
        elif resp_connect2.status_code != 200:
            print({"resp": "bad_new-token"})
            return JsonResponse({"resp": "bad_new-token"}, status=200)
        resp_connect3 = SuplierId(data["supplier_id"]).test(resp_connect2)
        if resp_connect3 and data["supplier_id"] != old_supplier_id:
            current_settings.supplier_id = data["supplier_id"]
        elif not resp_connect3:
            print({"resp": "bad_supplier_id"})
            return JsonResponse({"resp": "bad_supplier_id"}, status=200)

        current_settings.save()
        print(data)
        return JsonResponse({"ok": data}, status=200)


def api_tokens(request):
    context = {}
    if request.method == "POST":
        form = AddAPIToken(request.POST)
        if form.is_valid():
            wb_token = form.cleaned_data.get("api_key")
            token_name = form.cleaned_data.get("api_name")
            date_now = datetime.datetime.now(datetime.timezone.utc)
            user = request.user
            if Limits.objects.filter(
                client=user, start_date__lte=date_now, end_date__gte=date_now
            ).exists():
                order = Limits.objects.get(
                    client=user, start_date__lte=date_now, end_date__gte=date_now
                ).paid_info.order
                count_tokens = len(Client_tokens.objects.filter(client=request.user))
                if order.is_calculated == True:
                    user_limit = order.calculated_tariff.monitor
                elif order.tariff == "showroom":
                    user_limit = 1
                elif order.tariff == "market":
                    user_limit = 1
                elif order.tariff == "hypermarket":
                    user_limit = 5
                elif order.tariff == "magigrand":
                    user_limit = 15
                else:
                    user_limit = 0
                for order in Order.objects.filter(prolongation_to=order.id, paid_status=True):
                    user_limit += order.calculated_tariff.monitor

                if count_tokens + 1 > user_limit:
                    return JsonResponse({"resp": "limit"}, status=200)
            else:
                return JsonResponse({"resp": "tariff"}, status=200)
            resp_connect = X64ApiClient(wb_token).test()
            if resp_connect.status_code == 200:
                if API_tokens.objects.filter(token=wb_token).exists():
                    token_object = API_tokens.objects.get(token=wb_token)
                    if not Client_tokens.objects.filter(
                        token=token_object, client=request.user
                    ).exists():
                        Client_tokens.objects.create(
                            token=token_object, name=token_name, client=request.user
                        )
                else:
                    token_object = API_tokens.objects.create(token=wb_token)
                    Client_tokens.objects.create(
                        client=request.user, name=token_name, token=token_object
                    )
                token = Client_tokens.objects.get(
                    token=token_object, client=request.user
                )
                context["error"] = False
                context["message"] = "Токен добавлен!"
                # return JsonResponse({"resp": "ok", "id": token.id}, status=200)
                return redirect("home")
            else:
                context["error"] = True
                context["message"] = "Токен введен не верно"
                return JsonResponse({"resp": "bad token"}, status=200)
        return render(request, "apps/main_page.html", context)
    else:
        form = AddAPIToken()
        context["form"] = form
        objects = Client_tokens.objects.filter(client=request.user).order_by(
            "created_at"
        )
        context["objects"] = objects
        return render(request, "apps/api-tokens.html", context)


def api_delete(request, pk):
    Client_tokens.objects.get(id=pk, client=request.user).delete()
    return redirect("api-tokens")


def api_edit(request, pk):
    if request.method == "POST":
        form = AddAPIToken(request.POST)
        if form.is_valid():
            wb_token = form.cleaned_data.get("api_key")
            token_name = form.cleaned_data.get("api_name")
            resp_connect = X64ApiClient(wb_token).test()
            if resp_connect.status_code == 200:
                if not API_tokens.objects.filter(token=wb_token).exists():
                    token_object = API_tokens.objects.create(token=wb_token)
                else:
                    token_object = API_tokens.objects.get(token=wb_token)
                Client_tokens.objects.filter(id=pk).update(
                    name=token_name, token=token_object
                )
                return JsonResponse({"resp": "ok"}, status=200)
            else:
                return JsonResponse({"resp": "bad token"}, status=200)
        return JsonResponse({"resp": "bad token"}, status=200)
    # return redirect('api-tokens')


def update_order_data(request, wb_token):
    try:
        token = API_tokens.objects.get(token=wb_token)
        orders_all = X64ApiClient(wb_token).get_ordered(url="orders", days=90, flag=0)
        print(orders_all)
        orders_in_db = Orders.objects.filter(token=token).values_list(
            "income_id", flat=True
        )
        for order in orders_all:
            if order["incomeID"] not in orders_in_db:
                price = int(
                    order["totalPrice"] * (100 - order["discountPercent"]) / 100
                )
                Orders.objects.create(
                    token=token,
                    date=order["date"],
                    sku=order["nmId"],
                    name=order["subject"],
                    brand=order["brand"],
                    price=price,
                    income_id=order["incomeID"],
                )

        sales_all = X64ApiClient(wb_token).get_ordered(url="sales", days=90, flag=0)
        sales_in_db = Sales.objects.filter(token=token).values_list(
            "income_id", flat=True
        )
        for sale in sales_all:
            if sale["incomeID"] not in sales_in_db:
                price = int(sale["totalPrice"] * (100 - sale["discountPercent"]) / 100)
                Sales.objects.create(
                    token=token,
                    date=sale["date"],
                    sku=sale["nmId"],
                    name=sale["subject"],
                    brand=sale["brand"],
                    price=price,
                    income_id=sale["incomeID"],
                )
        # ClientSettings.objects.filter(client=request.user).update(wb_updated=datetime.datetime.now(datetime.timezone.utc))
        API_tokens.objects.filter(token=token.token).update(
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )
        return True
    except Exception as e:
        print(e)
        return False


def get_data_main(request, weeks_ago=None, brand=None, api_key=None):
    if weeks_ago == None:
        now = datetime.datetime.now(datetime.timezone.utc)
    else:
        now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=int(weeks_ago) * 7
        )
    if api_key == None:
        api_list = (
            Client_tokens.objects.filter(client=request.user)
            .order_by("created_at")
            .values("token")
        )
    else:
        api_list = [api_key]

    if brand == None:
        brand_list = (
            Orders.objects.filter(token__in=api_list).values("brand").distinct()
        )
    else:
        brand_list = [brand]
    orders = Orders.objects.filter(
        token__in=api_list,
        brand__in=brand_list,
        date__gte=(now - datetime.timedelta(days=7)),
    )
    orders_today = orders.filter(date__gte=now.date())
    orders_sum = sum([i.price for i in orders])
    orders_count = len(orders)
    orders_sum_diff = sum([i.price for i in orders_today])
    orders_count_diff = len(orders_today)

    sales = Sales.objects.filter(
        token__in=api_list,
        brand__in=brand_list,
        date__gte=(now - datetime.timedelta(days=7)),
    )
    sales_today = sales.filter(date__gte=now.date())
    sales_sum = sum([i.price for i in sales])
    sales_count = len(sales)
    sales_sum_diff = sum([i.price for i in sales_today])
    sales_count_diff = len(sales_today)

    sum_orders_products = (
        orders.values("sku", "name")
        .annotate(sum_price=Sum("price"), counter=Count("price"))
        .order_by("-sum_price")
    )
    sum_sales_products = (
        sales.values("sku", "name")
        .annotate(sum_price=Sum("price"), counter=Count("price"))
        .order_by("-sum_price")[:5]
    )
    best_products = []

    added_best_sku = []
    for sale in sum_sales_products:
        for order in sum_orders_products:
            if sale["sku"] == order["sku"]:
                cover = f"https://images.wbstatic.net/big/new/{str(sale['sku'])[:-4]}0000/{sale['sku']}-1.jpg"
                best_products.append(
                    {
                        "cover": cover,
                        "title": sale["name"],
                        "sku": sale["sku"],
                        "sum_sales": sale["sum_price"],
                        "sum_orders": order["sum_price"],
                        "count_sales": sale["counter"],
                        "count_orders": order["counter"],
                    }
                )
                added_best_sku.append(sale["sku"])
                continue
        if sale["sku"] not in added_best_sku:
            cover = f"https://images.wbstatic.net/big/new/{str(sale['sku'])[:-4]}0000/{sale['sku']}-1.jpg"
            best_products.append(
                {
                    "cover": cover,
                    "title": sale["name"],
                    "sku": sale["sku"],
                    "sum_sales": sale["sum_price"],
                    "sum_orders": "-",
                    "count_sales": sale["counter"],
                    "count_orders": "-",
                }
            )
            added_best_sku.append(sale["sku"])

    if len(added_best_sku) < 5:
        for order in sum_orders_products:
            if order["sku"] not in added_best_sku and len(added_best_sku) < 5:
                cover = f"https://images.wbstatic.net/big/new/{str(order['sku'])[:-4]}0000/{order['sku']}-1.jpg"
                best_products.append(
                    {
                        "cover": cover,
                        "title": order["name"],
                        "sku": order["sku"],
                        "sum_sales": "-",
                        "sum_orders": order["sum_price"],
                        "count_sales": "-",
                        "count_orders": order["counter"],
                    }
                )
                added_best_sku.append(order["sku"])
            elif len(added_best_sku) == 5:
                break

    buyout_2_week_ago = ProductBuyout.objects.filter(
        client=request.user,
        product__brand__name__in=brand_list,
        updated_at__lte=(now - datetime.timedelta(days=7)),
        updated_at__gte=(now - datetime.timedelta(days=15)),
        status="done",
    )
    buyout_last_week = ProductBuyout.objects.filter(
        client=request.user,
        product__brand__name__in=brand_list,
        updated_at__gte=(now - datetime.timedelta(days=7)),
        status="done",
    )
    wb_tokens = Client_tokens.objects.filter(client=request.user).order_by("created_at")
    buyout_stat_dates = []
    buyout_stat_count = []
    dashboard = {
        "sum_sales": [],
        "count_sales": [],
        "sum_orders": [],
        "count_orders": [],
        "buyout_order_sum": [],
        "buyout_order_count": [],
        "buyout_done_sum": [],
        "buyout_done_count": [],
    }
    weeks_alaliable = []
    brands = Orders.objects.filter(token__in=api_list).values("brand").distinct()
    for i in range(1, 5):
        temp_date_start = now - datetime.timedelta(days=i * 7)
        temp_date_end = temp_date_start + datetime.timedelta(days=7)
        weeks_alaliable.append(
            {
                "start": temp_date_start.date(),
                "end": temp_date_end.date(),
                "w_ago": i - 1,
            }
        )
    for i in reversed(range(0, 7)):
        start = (now - datetime.timedelta(days=i)).date()
        end = datetime.datetime.strptime(
            start.strftime("%Y%m%d"), "%Y%m%d"
        ) + datetime.timedelta(days=1)
        date_buyouts = buyout_last_week.filter(
            updated_at__gte=start, updated_at__lte=end
        )
        date_sales = Sales.objects.filter(
            token__in=api_list, brand__in=brand_list, date__gte=start, date__lte=end
        )
        date_orders = Orders.objects.filter(
            token__in=api_list, brand__in=brand_list, date__gte=start, date__lte=end
        )
        date_buyouts_order = ProductBuyout.objects.filter(
            updated_at__gte=start,
            product__brand__name__in=brand_list,
            updated_at__lte=end,
            client=request.user,
        ).filter((Q(status="done") | Q(status="ready")) | Q(status="delivery"))
        dashboard["sum_sales"].append(sum([i.price for i in date_sales]))
        dashboard["count_sales"].append(len(date_sales))
        dashboard["sum_orders"].append(sum([i.price for i in date_orders]))
        dashboard["count_orders"].append(len(date_orders))
        dashboard["buyout_order_sum"].append(
            sum([i.price_buy for i in date_buyouts_order])
        )
        dashboard["buyout_order_count"].append(len(date_buyouts_order))
        dashboard["buyout_done_sum"].append(sum([i.price_buy for i in date_buyouts]))
        dashboard["buyout_done_count"].append(len(date_buyouts))

        buyout_stat_dates.append(start.strftime("%d.%m"))
        buyout_stat_count.append(len(date_buyouts))

    context = {
        "orders_sum": orders_sum,
        "orders_count": orders_count,
        "orders_sum_diff": orders_sum_diff,
        "orders_count_diff": orders_count_diff,
        "sales_sum": sales_sum,
        "sales_count": sales_count,
        "sales_sum_diff": sales_sum_diff,
        "sales_count_diff": sales_count_diff,
        "best_products": best_products,
        "dashboard": dashboard,
    }
    context["count_buyout"] = len(
        ProductBuyout.objects.filter(
            client=request.user, product__brand__name__in=brand_list, status="done"
        )
    )
    context["count_review"] = len(
        AddingReview.objects.filter(
            client=request.user,
            buyout__product__brand__name__in=brand_list,
            status="done",
        )
    )
    context["count_question"] = len(
        BoostQuestion.objects.filter(client=request.user, status="done")
    )
    context["count_like"] = len(
        BoostLikeReview.objects.filter(client=request.user, status="done")
    ) + len(BoostLike.objects.filter(client=request.user, status="done"))
    context["buyout_stat_dates"] = json.dumps(buyout_stat_dates)
    context["buyout_stat_count"] = buyout_stat_count
    context["wb_tokens"] = wb_tokens
    context["weeks_alaliable"] = weeks_alaliable
    context["brands"] = brands
    if len(buyout_2_week_ago) == 0 and len(buyout_last_week) != 0:
        context["buyout_diff_week"] = "+100%"
    elif len(buyout_2_week_ago) == 0 and len(buyout_last_week) == 0:
        context["buyout_diff_week"] = "0%"
    else:
        diff_buyout = len(buyout_last_week) / len(buyout_2_week_ago)
        if diff_buyout > 1:
            context["buyout_diff_week"] = (
                "+" + str(round((diff_buyout - 1) * 100)) + "%"
            )
        elif diff_buyout == 1:
            context["buyout_diff_week"] = "0%"
        else:
            context["buyout_diff_week"] = (
                "-" + str(round((1 - diff_buyout) * 100)) + "%"
            )

    return context


def products(request):
    context = {"resp": "data"}
    return render(request, "apps/products.html", context)
