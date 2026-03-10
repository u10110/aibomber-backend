import datetime
from atexit import register
from datetime import timezone

from django import template
from django.contrib.auth import get_user_model

from apps.billing.helper import Helper
from apps.billing.models import Limits, Order, Paid, UnicTariff
from apps.home.models import ClientSettings

User = get_user_model()

register = template.Library()


@register.simple_tag
def show_limits(r_user):
    # print(Helper.get_max_limit('buyout_limit', r_user.id))
    try:
        user = User.objects.get(id=r_user.id)
        date_now = datetime.datetime.now(datetime.timezone.utc)
        limits = Limits.objects.get(
            client=user, start_date__lte=date_now, end_date__gte=date_now
        )

        paid = limits.paid_info
        order = paid.order
        if order.is_calculated == True:
            tariff = order.calculated_tariff
            limits.tariff = "Собственный"
        else:
            tariff = UnicTariff.objects.get(title=order.tariff)
            if tariff.title == "showroom":
                limits.tariff = "Шоурум"
            elif tariff.title == "market":
                limits.tariff = "Магазин"
            elif tariff.title == "hypermarket":
                limits.tariff = "Гипермаркет"
            elif tariff.title == "magigrand":
                limits.tariff = "Магигранд"
            else:
                limits.tariff = tariff.title

        for_max_limits = Helper(r_user.id)
        limits.buyout_limit_max = for_max_limits.get_max_limit("buyout_limit")
        limits.review_limit_max = for_max_limits.get_max_limit("review_limit")
        limits.question_limit_max = for_max_limits.get_max_limit("question_limit")

        limits.like_limit_max = for_max_limits.get_max_limit("like_limit")
        limits.like_review_max = for_max_limits.get_max_limit("like_review_limit")
        limits.like_limit_sum = limits.like_limit + limits.like_review_limit
        limits.course_autobuy = for_max_limits.get_max_limit("course_autobuy")

        return limits
    except Exception as e:
        print(e)
        return False


@register.simple_tag
def tariff_end_date(r_user):
    try:
        user = User.objects.get(id=r_user.id)
        end_date = Paid.objects.filter(client=user).latest("end_date").end_date
        return end_date
    except Exception as e:
        print(e)
        return False


@register.simple_tag
def get_tg_token(r_user):
    try:
        user = ClientSettings.objects.get(client_id=r_user.id)
        token = user.tg_token
        return token
    except Exception as e:
        print(e)
        return False


@register.simple_tag
def is_tg_active(r_user):
    try:
        user = ClientSettings.objects.get(client_id=r_user.id)
        token = user.tg_chat_id
        if token != None:
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False
