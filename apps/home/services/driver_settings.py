import re

from decouple import config
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from .proxy import get_proxy


def init_driver():

    proxy = get_proxy()
    proxy = re.sub(".*@", "", proxy["http"])
    logger.debug(f"{proxy}")
    options = webdriver.ChromeOptions()
    options.add_argument(f"--proxy-server=socks5://{proxy}")
    options.add_argument("--disable-blink-features=AutomationControlled")

    desired_capabilities = {
        "browserName": "chrome",
        "browserVersion": "98.0",
        "selenoid:options": {
            "enableVNC": True,
            "screenResolution": "1500x1050x24",
            "sessionTimeout": "6m",
        },
    }
    driver = webdriver.Remote(
        command_executor=config("SELENOID_URL"),
        desired_capabilities=desired_capabilities,
        options=options,
    )
    return driver
