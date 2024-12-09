import random
from random import shuffle

import requests
from apps.home.models import Proxy
from loguru import logger


def get_proxy(tries=0):
    proxy = Proxy.objects.all()
    proxy = random.choice(proxy)
    proxy = proxy.value
    logger.debug(f"Was get proxy {proxy}")
    proxy = {"http": proxy, "https": proxy}
    return proxy


def get_proxy_list(tries=0):
    proxy_list = []
    proxies = Proxy.objects.all()
    for proxy in proxies:
        proxy_list.append({"http": proxy.value, "https": proxy.value})

    shuffle(proxy_list)
    return proxy_list
