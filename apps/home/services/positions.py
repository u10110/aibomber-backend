import datetime

from apps.billing.models import Limits, Order, Paid, UnicTariff
from apps.home.forms import *
from apps.home.helper import Helper
from apps.home.models import ClientPhrase, ClientProduct, Phrase
from loguru import logger


def add_new_phrase(request, context):
    logged_in_user = request.user
    form = SearchPromotionForm(request.POST)
    if form.is_valid():
        date_now = datetime.datetime.now(datetime.timezone.utc)
        limits = Limits.objects.filter(client_id=request.user.id)[0]

        limit_count_now = ClientPhrase.objects.filter(
            client_id=logged_in_user.id
        ).count()

        if not limits or limits.end_date < date_now.date():
            context["error"] = False
            context["error_message"] = "Необходимо приобрести тариф"
            return context
        elif limits.search_promotion_limit <= limit_count_now:
            context["error"] = False
            context["error_message"] = "Вы достигли допустимого лимита вашего тарифа"
            return context
        else:
            data = {
                "marketplace": form.cleaned_data.get("marketplace"),
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
            else:
                print(product)
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
                print(new_product)
                if ClientPhrase.objects.filter(
                    product=new_product[0], client_id=logged_in_user.id
                ).exists():
                    context["error"] = False
                    context["error_message"] = "Артикул уже добавлен"
                    return context
                print(data)

                # search_promotion = ClientPhrase.objects.create(
                #     marketplace_id=marketplace_id,
                #     status="active",
                #     product=new_product[0],
                #     client_id=logged_in_user.id,
                # )

                search_promotion = ClientPhrase.objects.create(
                    marketplace_id=marketplace_id,
                    status="active",
                    product=new_product[0],
                    client_id=logged_in_user.id,
                    is_search_promotion=True,
                )

                return context
