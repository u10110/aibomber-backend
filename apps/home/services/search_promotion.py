import datetime

from apps.billing.models import Limits, Order, Paid, UnicTariff
from apps.home.forms import *
from apps.home.helper import Helper
from apps.home.models import ClientPhrase, ClientProduct, Phrase
from apps.home.services.elastic import ES
from loguru import logger


def get_search_promotion_limits(user_id, is_search_promotion):
    date_now = datetime.datetime.now(datetime.timezone.utc)
    limits = 0
    paid = Paid.objects.filter(
        client_id=user_id, start_date__lte=date_now, end_date__gte=date_now
    )
    if paid.exists():
        active_paid = paid[0]
        if is_search_promotion:
            if active_paid.order.tariff == "custom":
                limits += active_paid.order.calculated_tariff.search_promotion
            order_id_current = active_paid.order.id
        else:
            if active_paid.order.tariff == "custom":
                limits += active_paid.order.calculated_tariff.monitoring_kz
            else:
                limits += UnicTariff.objects.get(
                    title=active_paid.order.tariff
                ).positions_limit
        order_id_current = active_paid.order.id
        for prolongation_order in Order.objects.filter(
            prolongation_to=order_id_current, paid_status=True
        ):
            if is_search_promotion:
                limits += prolongation_order.calculated_tariff.search_promotion
            else:
                limits += prolongation_order.calculated_tariff.monitoring_kz
    return limits


def get_count_search_promotion_limits(user_id, is_search_promotion):
    if is_search_promotion:
        limit_count_now = ClientPhrase.objects.filter(
            client_id=user_id, is_search_promotion=True
        ).count()
    else:
        limit_count_now = ClientPhrase.objects.filter(
            client_id=user_id, is_search_promotion=False
        ).count()
    return limit_count_now


def add_new_search_promotion(request, is_search_promotion, context):
    logged_in_user = request.user

    form = SearchPromotionForm(request.POST)

    if form.is_valid():
        if not form.cleaned_data.get("marketplace"):
            form.cleaned_data["marketplace"] = "Wildberries"
        date_now = datetime.datetime.now(datetime.timezone.utc)
        limits = 0
        if Paid.objects.filter(
            client_id=request.user.id, start_date__lte=date_now, end_date__gte=date_now
        ).exists():
            limits += get_search_promotion_limits(request.user.id, is_search_promotion)
        else:
            context["error"] = False
            context["error_message"] = "Необходимо приобрести тариф"
            return context

        if is_search_promotion:
            limit_count_now = ClientPhrase.objects.filter(
                client_id=logged_in_user.id, is_search_promotion=True
            ).count()
        else:
            limit_count_now = ClientPhrase.objects.filter(
                client_id=logged_in_user.id, is_search_promotion=False
            ).count()

        if limit_count_now >= limits:
            context["error"] = False
            context["error_message"] = "Вы достигли допустимого лимита вашего тарифа"
            return context
        else:
            data = {
                "marketplace": form.cleaned_data["marketplace"],
                "sku": form.cleaned_data.get("sku"),
            }
            try:
                product = Helper.check_sku(data["sku"], 1)
            except:
                context["error"] = False
                context["error_message"] = "SKU не найден"
                return context
            logger.debug(f"{product}")
            if not product:
                wrong_link = True
                context["error"] = False
                context["error_message"] = "SKU не найден"
                return context
            else:
                marketplace_id = Helper.marketplace_id(data["marketplace"])
                if not ClientProduct.objects.filter(
                    sku=data["sku"], client_id=logged_in_user.id
                ).exists():
                    ClientProduct.objects.create(
                        sku=data["sku"],
                        title=product["title"],
                        cover=product["cover"],
                        price=product["price"],
                        status="awaiting",
                        client_id=logged_in_user.id,
                        marketplace_id=marketplace_id,
                        brand_id=product["brand_id"],
                    )

                new_product = ClientProduct.objects.only("id").filter(
                    sku=data["sku"], client_id=logged_in_user.id
                )
                if ClientPhrase.objects.filter(
                    product=new_product[0], client_id=logged_in_user.id
                ).exists():
                    client_phrase = ClientPhrase.objects.get(
                        product=new_product[0], client_id=logged_in_user.id
                    )
                    if client_phrase.is_search_promotion is True:
                        context["error"] = False
                        context["error_message"] = "Артикул уже добавлен"
                        return context
                    else:
                        search_promotion = ClientPhrase.objects.filter(
                            product=new_product[0], client_id=logged_in_user.id
                        ).update(
                            is_search_promotion=True,
                        )
                        if is_search_promotion:
                            return context

                search_promotion = ClientPhrase.objects.create(
                    marketplace_id=marketplace_id,
                    status="active",
                    product=new_product[0],
                    client_id=logged_in_user.id,
                    is_search_promotion=is_search_promotion,
                )

                return context
    else:
        context["error"] = False
        context["error_message"] = "Введите ску"
        return context


def get_search_promotions(
    request,
    is_search_promotion,
    context,
    pk="",
    date_start_raw=False,
    date_end_raw=False,
):
    if not date_end_raw:
        # date_end_raw = datetime.datetime.now()
        date_end_raw = datetime.datetime.today() - datetime.timedelta(1)
        date_end = datetime.datetime.strftime(date_end_raw, "%Y-%m-%d")
        date_start_raw = datetime.datetime.now() - datetime.timedelta(29)
        date_start = datetime.datetime.strftime(date_start_raw, "%Y-%m-%d")

    date_end = datetime.datetime.strftime(date_end_raw, "%Y-%m-%d")
    date_start = datetime.datetime.strftime(date_start_raw, "%Y-%m-%d")
    print(f"ss{date_end_raw}")
    print(f"ss{date_start_raw}")

    all_phrases = []

    delta = (
        date_end_raw + datetime.timedelta(1)
    ) - date_start_raw  # this shit is for Linux WTF
    # delta = date_end_raw - date_start_raw  # this shit is for WIndows WTF

    print(f"ss{delta}")
    date_range = []
    for date in range(delta.days + 1):
        date_range.append(
            datetime.datetime.strftime(
                date_start_raw + datetime.timedelta(date), "%Y-%m-%d"
            )
        )

    date_yesterday = date_end_raw - datetime.timedelta(1)
    date_yesterday = datetime.datetime.strftime(date_yesterday, "%Y-%m-%d")

    es = ES()
    logged_in_user = request.user

    if "details" in request.path:
        item = ClientPhrase.objects.get(id=pk)
        related = [item]
    else:
        if is_search_promotion:
            related = (
                ClientPhrase.objects.select_related("marketplace")
                .select_related("product")
                .filter(
                    client=logged_in_user,
                    is_search_promotion=is_search_promotion,
                )
            )
        else:
            related = (
                ClientPhrase.objects.select_related("marketplace")
                .select_related("product")
                .filter(
                    client=logged_in_user,
                )
            )

    for item in related:
        position_history = es.get_doc_by_sku(item.product.sku)

        for p in position_history:  # TODO remove this after clean db
            p["phrase"] = p["phrase"].replace("'", "")

        if position_history:
            item.parse_status = "done"
            item.visibility_today = 0
            item.visibility_yesterday = 0
            positions_today = []
            positions_yesterday = []
            positions_before = []
            item.phrases = []
            item.dates_stats = []
            positions_in_start = []
            positions_in_end = []
            phrase_l = []
            for phrase in position_history:
                phrase_l.append(phrase["phrase"])
            phrase_pg = Phrase.objects.filter(value__in=phrase_l)

            publicate_check = []
            for phrase in position_history:
                if phrase["phrase"] not in all_phrases:
                    all_phrases.append(phrase["phrase"])
                duplicate = False
                if datetime.datetime.strptime(
                    date_range[0], "%Y-%m-%d"
                ) < datetime.datetime.strptime("2022-09-13", "%Y-%m-%d"):
                    date_for_check_start = "2022-09-13"
                else:
                    date_for_check_start = date_range[0]
                if phrase["date"] == date_for_check_start:
                    for ph in positions_in_start:
                        if phrase["phrase"] == ph[0]:
                            duplicate = True
                    if not duplicate:
                        positions_in_start.append(
                            [phrase["phrase"], phrase["position"]]
                        )
                if phrase["date"] == date_range[-1]:
                    for ph in positions_in_end:
                        if phrase["phrase"] == ph[0]:
                            duplicate = True
                    if not duplicate:
                        positions_in_end.append([phrase["phrase"], phrase["position"]])

                check = False
                if publicate_check:
                    for ch in publicate_check:
                        if (
                            phrase["date"] == ch["date"]
                            and phrase["phrase"] == ch["phrase"]
                        ):
                            check = True
                            break
                if not check:
                    publicate_check.append(
                        {"date": phrase["date"], "phrase": phrase["phrase"]}
                    )
                    if phrase["date"] == date_end:
                        # if phrase[date]
                        positions_today.append(phrase["position"])
                        item.visibility_today += 1
                        # if phrase[""]
                    if phrase["date"] == date_yesterday:
                        positions_yesterday.append(phrase["position"])
                        item.visibility_yesterday += 1
                    if phrase["date"] == positions_before:
                        positions_before.append(phrase["position"])
                        item.visibility_before += 1

                frequency = False
                for obj in phrase_pg:
                    if phrase["phrase"] == obj.value:
                        frequency = obj.frequency
                        break
                if not frequency:
                    frequency = 0

                check = False
                for phh in item.phrases:
                    if phrase["phrase"] == phh["phrase"]:
                        check = True
                        break
                if check is False:
                    if phrase["date"] in date_range:
                        item.phrases.append(
                            {
                                "phrase": phrase["phrase"],
                                "frequency": frequency,
                                "dates": [],
                                "positions": [],
                                phrase["date"]: [phrase["position"], 1],
                            }
                        )

                for i, phrasee in enumerate(item.phrases):
                    if phrase["phrase"] == phrasee["phrase"]:
                        ysterday_pos = False
                        t = datetime.datetime.strptime(phrase["date"], "%Y-%m-%d")
                        d = t - datetime.timedelta(1)
                        d = datetime.datetime.strftime(d, "%Y-%m-%d")
                        t = datetime.datetime.strftime(t, "%Y-%m-%d")
                        for z in position_history:
                            if phrase["phrase"] == z["phrase"] and z["date"] == d:
                                ysterday_pos = z["position"]

                        if ysterday_pos:
                            # dynamics = ysterday_pos - phrase["position"]
                            dynamics = ysterday_pos - phrase["position"]
                        else:
                            dynamics = phrase["position"]
                        if phrase["date"] in date_range:
                            item.phrases[i]["dates"].append(phrase["date"])
                            item.phrases[i]["positions"].append(phrase["position"])
                            item.phrases[i].update(
                                {phrase["date"]: [phrase["position"], dynamics]}
                            )
            for i, phrasee in enumerate(item.phrases):
                phrasee.update(
                    {
                        "averagePosition": round(
                            sum(phrasee["positions"]) / len(phrasee["positions"])
                        )
                    }
                )

            item.average_position_by_dates = []
            item.visibility_by_dates = []
            for date in date_range:
                visibility_by_dates = 0
                average_position_by_dates = []
                for i in item.phrases:
                    for key in i:
                        if date == key:
                            visibility_by_dates += 1
                            average_position_by_dates.append(i[key][0])
                if average_position_by_dates:
                    a = round(
                        sum(average_position_by_dates) / len(average_position_by_dates)
                    )
                    item.average_position_by_dates.append({date: a})
                    item.visibility_by_dates.append({date: visibility_by_dates})

            item.le3 = 0
            item.le10 = 0
            item.g3e10 = 0
            item.ge11le30 = 0
            item.ge31le50 = 0
            item.ge51le100 = 0
            item.g100 = 0
            item.g10le100 = 0
            item.yle3 = 0
            item.yle10 = 0
            item.yg3e10 = 0
            item.yge11le30 = 0
            item.yge31le50 = 0
            item.yge51le100 = 0
            item.yg100 = 0
            item.yg10le100 = 0
            item.average_position_today = 0
            item.average_position_yesterday = 0
            for position in positions_in_end:
                item.average_position_today += int(position[1])
                if int(position[1]) > 100:
                    item.g100 += 1
                if int(position[1]) <= 3:
                    item.le3 += 1
                if 3 < int(position[1]) <= 10:
                    item.g3e10 += 1
                if int(position[1]) <= 10:
                    item.le10 += 1
                if 11 <= int(position[1]) <= 30:
                    item.ge11le30 += 1
                if 31 <= int(position[1]) <= 50:
                    item.ge31le50 += 1
                if 51 <= int(position[1]) <= 100:
                    item.ge51le100 += 1
                if 10 < int(position[1]) <= 100:
                    item.g10le100 += 1
            item.g11le50 = item.ge11le30 + item.ge31le50

            for position in positions_in_start:
                item.average_position_yesterday += int(position[1])
                if int(position[1]) > 100:
                    item.yg100 += 1
                if int(position[1]) <= 3:
                    item.yle3 += 1
                if 3 < int(position[1]) <= 10:
                    item.yg3e10 += 1
                if int(position[1]) <= 10:
                    item.yle10 += 1
                if 11 <= int(position[1]) <= 30:
                    item.yge11le30 += 1
                if 31 <= int(position[1]) <= 50:
                    item.yge31le50 += 1
                if 51 <= int(position[1]) <= 100:
                    item.yge51le100 += 1
                if 10 < int(position[1]) <= 100:
                    item.yg10le100 += 1

            item.le3_change = item.g100 - item.yg100
            item.le10_change = item.le10 - item.yle10
            item.g3e10_change = item.g3e10 - item.yg3e10
            item.ge11le30_change = item.ge11le30 - item.yge11le30
            item.ge31le50_change = item.ge31le50 - item.yge31le50
            item.ge51le100_change = item.ge51le100 - item.yge51le100
            item.g100_change = item.g100 - item.yg100
            item.g10le100_change = item.g10le100 - item.yg10le100

            if positions_today:
                print(f"ssss{item.average_position_today} {len(positions_today)}")
                item.average_position_today = item.average_position_today / len(
                    positions_today
                )
                item.g100_count = item.g100 / len(positions_today)

                item.le3_procent = round(item.le3 * 100 / len(positions_today), 1)
                item.g3e10_procent = round(item.g3e10 * 100 / len(positions_today), 1)
                item.ge11le30_procent = round(
                    item.ge11le30 * 100 / len(positions_today), 1
                )
                item.ge31le50_procent = round(
                    item.ge31le50 * 100 / len(positions_today), 1
                )
                item.ge51le100_procent = round(
                    item.ge51le100 * 100 / len(positions_today), 1
                )
                item.g100_procent = round(item.g100 * 100 / len(positions_today), 1)

            # item.visibility_60days = [10, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 56, 55, 40, 65, 59, 80, 81, 56, 55, 40, 65, 59, 80, 81, 56, 55, 40,65, 59,]
            item.average_60days = []
            for i in item.average_position_by_dates:
                for key, value in i.items():
                    item.average_60days.append(value)
            if len(item.average_60days) < 30:
                for i in range(len(date_range) - len(item.average_60days)):
                    item.average_60days = [1] + item.average_60days
            item.visibility_60days = []
            for i in item.visibility_by_dates:
                for key, value in i.items():
                    item.visibility_60days.append(value)
            if len(item.visibility_60days) < 30:
                for i in range(len(date_range) - len(item.visibility_60days)):
                    item.visibility_60days = [1] + item.visibility_60days

            trash = {}
            for i in item.average_position_by_dates:
                for key in i:
                    trash.update({key: i[key]})
            item.average_position_by_dates = trash

            trash = {}
            for i in item.visibility_by_dates:
                for key in i:
                    trash.update({key: i[key]})
            item.visibility_by_dates = trash
            item.average_position_by_dates
            item.visibility_by_dates

            item.all_phrases = all_phrases

            # item.average_position = int(average_position)

            item.position_increased = 0
            item.position_nochanged = 0
            item.position_decreased = 0
            for ph_end in positions_in_end:
                if positions_in_start:
                    is_instart = False
                    for ph_start in positions_in_start:
                        if ph_end[0] == ph_start[0]:
                            if ph_end[1] < ph_start[1]:
                                item.position_increased += 1
                                is_instart = True
                            elif ph_end[1] == ph_start[1]:
                                item.position_nochanged += 1
                                is_instart = True
                            elif ph_end[1] > ph_start[1]:
                                item.position_decreased += 1
                                is_instart = True
                    if not is_instart:
                        item.position_increased += 1
                else:
                    item.position_increased += 1
            for ph_start in positions_in_start:
                is_inend = False
                for ph_end in positions_in_end:
                    if ph_end[0] == ph_start[0]:
                        is_inend = True
                if not is_inend:
                    item.position_decreased += 1

            print(f"ss{item.average_position_by_dates}")
            if date_end in item.average_position_by_dates:
                item.average_position_today = item.average_position_by_dates[date_end]
                item.visiability_today = item.visibility_by_dates[date_end]
            else:
                item.average_position_today = 0
                item.visiability_today = 0
            if date_yesterday in item.average_position_by_dates:
                item.average_position_today_yesterday = item.average_position_by_dates[
                    date_yesterday
                ]
                item.visiability_yesterday = item.visibility_by_dates[date_yesterday]
            else:
                item.average_position_today_yesterday = 0
                item.visiability_yesterday = 0
            item.average_position_change = (
                item.average_position_today_yesterday - item.average_position_today
            )
            item.visiability_change = (
                item.visiability_today - item.visiability_yesterday
            )

            summ = (
                item.position_increased
                + item.position_nochanged
                + item.position_decreased
            )
            item.position_increased_procent = (
                round(item.position_increased * 100 / summ)
                if item.position_increased != 0
                else 0
            )
            item.position_nochanged_procent = (
                round(item.position_nochanged * 100 / summ)
                if item.position_nochanged != 0
                else 0
            )
            item.position_decreased_procent = (
                round(item.position_decreased * 100 / summ)
                if item.position_decreased != 0
                else 0
            )

            item.phrase_count = len(item.phrases)
        else:
            item.parse_status = "parsing"

        if item:
            context["objects"].append(item)
    from pprint import pprint

    return context


def get_frequency(phrase_list):
    ph_fr = Phrase.objects.filter(value__in=phrase_list)
    context = {}
    for phrase in phrase_list:
        frequency = False
        for obj in ph_fr:
            if phrase == obj.value:
                frequency = obj.frequency
                break
        if not frequency:
            frequency = 0
        context.update({phrase: frequency})
    return context
