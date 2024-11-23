import re

from apps.billing.models import Bank


def get_sbp_links(sbp_url):
    sbp_token = re.findall("(?<=qr\.nspk\.ru/).*?(?=\?)", sbp_url)[0]

    selected_banks = Bank.objects.all()

    for_buttons = []
    for bank in selected_banks:
        icon = f"https://qr.nspk.ru/proxyapp/logo/bank{bank.code}.png"
        link = f"bank{bank.code}://qr.nspk.ru/{sbp_token}"
        for_buttons.append({"title": bank.name_rus, "icon": icon, "url": link})
    sending_data = {"data": for_buttons}
    print(sending_data)
    return sending_data
