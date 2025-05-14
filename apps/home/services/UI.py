import pickle
import time

from decouple import config
from loguru import logger
from selenium.webdriver.common.by import By

from . import driver_settings, minio



def create_ui_instance(phone):
    driver = driver_settings.init_driver()

    selenium_host = config("SELENOID_UI_URL")
    selenium_link = f"{selenium_host}sessions/{driver.session_id}"

    ru_url = "https://wildberries.ru/lk/myorders/delivery"
    # ru_url = "https://wildberries.ru/lk"
    minio_service.get_obj(phone, f"data/cookies/{phone}")

    driver.get(ru_url)
    for cookie in pickle.load(open(f"data/cookies/{phone}", "rb")):
        driver.add_cookie(cookie)
    driver.get(ru_url)

    time.sleep(3)

    # user_name = driver.find_element(By.CLASS_NAME, "lk-item__title").text
    logger.info(f"{phone} Good account!")
    return selenium_link
