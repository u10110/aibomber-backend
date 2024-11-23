import multiprocessing as mp
from multiprocessing import Pool

from apps.alert.services.wb_api import WbAPI
from apps.home.models import Phrase


def get(ph):
    import django

    django.setup()
    print(ph.value)
    wb_api = WbAPI()
    response = wb_api.get_search(ph.value)
    if response and "data" in response:
        total = response["data"]["total"]
        return {
            "phrases": ph.value,
            "frequencyMonthly": ph.frequency,
            "frequencyAverageDay": ph.frequency / 30,
            "countProducts": total,
        }


def thread_function(ph):
    wb_api = WbAPI()
    print(ph.value)
    response = wb_api.get_search(ph.value)
    print(1)
    if response and response and "data" in response:
        total = response["data"]["total"]
        return {
            "phrases": ph.value,
            "frequencyMonthly": ph.frequency,
            "frequencyAverageDay": ph.frequency / 30,
            "countProducts": total,
        }
    else:
        return None


def get_phrases(phrase):

    context = []
    wb_api = WbAPI()
    phs = Phrase.objects.filter(value__contains=phrase)
    if phs:

        for ph in phs:
            context.append(
                {
                    "id": ph.id,
                    "phrases": ph.value,
                    "frequencyMonthly": ph.frequency,
                    "frequencyAverageDay": ph.frequency / 30,
                    "countProducts": ph.count_products,
                }
            )
    return context
