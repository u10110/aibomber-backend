from datetime import timedelta, timezone, datetime
from apps.billing.models import UnicTariff


def get_earned_referal(objects, bonus, orders):
    earned = 0
    for order in orders:
        if order.promocode and not order.promocode.is_manager:
            continue
        if not order.price:
            continue
        if order.tariff == 'custom':
            tariff = 'Собственный'
        else:
            tariff = UnicTariff.objects.get(title=order.tariff).descriptions
        earned += order.price * (bonus / 100)
        objects.append(
            {
                "id": order.client.id,
                "info": f"Покупка тарифа {tariff}",
                "status": "Пополнение",
                "sum": order.price,
                "bonus": order.price * (bonus / 100),
                "percentage": bonus
            }
        )
    return earned


def referal_live(privileged, date_joined):
    date_now = datetime.now(timezone.utc)
    ref_live = 360 if privileged else 180
    date_login = date_joined + timedelta(days=ref_live)
    if date_now > date_login:
        return False
    return True
