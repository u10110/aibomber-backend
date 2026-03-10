import requests

from apps.alert.views import TELEGRAM_TOKEN
from apps.home.models import ClientSettings


def send_message_all_tg_users(message):
    tg_id_list = ClientSettings.objects.values("tg_chat_id")
    if tg_id_list:
        for item in tg_id_list:
            tg_id = item.get("tg_chat_id")
            if tg_id:
                try:
                    requests.post(
                        url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        data=dict(chat_id=int(tg_id), text=message, parse_mode="Markdown"),
                    )
                except Exception as error:
                    pass
        return True
    return False
