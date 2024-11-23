from datetime import datetime, timedelta

import requests
import time
from apps.billing.models import Limits
from apps.home.models import ProductBuyout
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from .wb_api import WbClientAPI


def order_check(
    code1s,
    buyout_id,
    wb_client_api,
    rId,
    orderId,
):
    print(f"Checker started with {code1s},{buyout_id},{wb_client_api},{rId},{orderId},")

    def job(middle_date, code1s, buyout_id, cookie, rId):
        time.sleep(3)
        print(f"orderId is {orderId}, rId is {rId}")

        def get_pay_check(wb_client_api):
            response = wb_client_api.get_checks()
            for receipt in response["value"]["data"]["receipts"]:
                link = receipt["link"]
                response = requests.get(link)
                if rId in response.text:
                    return link

        def get_rid(response):
            if not response:
                return None
            for position in response["value"]["data"]["positionsModel"]["positions"]:
                if code1s == position["code1S"]:
                    return position["rId"]
                else:
                    return None

        wb_client_api = WbClientAPI(cookie)

        response = wb_client_api.get_order(orderId)
        rId = get_rid(response)
        print(f"rId is {rId}")
        now = datetime.now()

        middle_date_e = middle_date + timedelta(seconds=5)

        if end_date <= now:
            print(f"bad_pay {now}")
            response = wb_client_api.order_cancel(rId)
            print(response)

            # scheduler.shutdown()
            if scheduler.get_jobs():
                scheduler.remove_job(str(buyout_id))

        elif now < end_date:
            print(response)
            if (
                "orderPaymentStatus" in response["value"]["data"]["order"]
                and response["value"]["data"]["order"]["orderPaymentStatus"]
                == "success"
            ):
                print(f"{code1s} finded!")
                # check_link = get_pay_check(wb_client_api)
                ProductBuyout.objects.filter(id=buyout_id).update(
                    status="delivery",
                    payment_status="done",
                    # pay_check=check_link,
                )
                profile = wb_client_api.get_profile()
                logger.debug(f"{profile}")
                for card in profile["value"]["data"]["maskedCards"]:
                    wb_client_api.delete_card(card["id"])

                # scheduler.shutdown()
                if scheduler.get_jobs():
                    scheduler.remove_job(str(buyout_id))
            else:
                print(f"{code1s} not finded orderPaymentStatus!")

    scheduler = BackgroundScheduler()
    start_date = datetime.now()
    end_date = start_date + timedelta(seconds=550)
    middle_date = start_date + timedelta(seconds=300)
    scheduler.add_job(
        job,
        "interval",
        args=[middle_date, code1s, buyout_id, wb_client_api, rId],
        seconds=5,
        start_date=start_date,
        end_date=end_date,
        id=str(buyout_id)
        
    )
    scheduler.start()
