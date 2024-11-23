import json
import re

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from apps.home.helper import Helper
from apps.home.services.search_promotion import get_frequency
from apps.seo.forms import PhraseIntersection
from apps.seo.services.product_card import get_product_card
from apps.seo.services.selection_requests import get_phrases
from apps.seo.services.seo_group_search import get_group_search


def product_card(request):
    logged_in_user = request.user
    context = {"objects": []}
    wrong_link = False
    if request.method == "POST":
        sku = request.POST["sku"]
        sku = re.findall(r"\d+", sku)[0]
        context = get_product_card(context, sku)

    if "error" in context and context["error"] == "sku not found":
        messages.warning(request, "Товар не найден")
        return HttpResponseRedirect("/product-card-search/", context)
    if wrong_link:
        context["error"] = False
        context["error_message"] = "Артикул не найден!"
    return render(request, "apps/product-card.html", context)


def seo_group_result(request):
    logged_in_user = request.user
    context = {"objects": []}
    wrong_link = False
    if request.method == "POST":
        form = PhraseIntersection(request.POST)
        print(form)
        groupA = list(
            filter(None, re.split(";|\*| |,|\r\n", form.cleaned_data.get("groupA")))
        )
        groupB = list(
            filter(None, re.split(";|\*| |,|\r\n", form.cleaned_data.get("groupB")))
        )

        context = get_group_search(context, groupA, groupB)
    if wrong_link:
        context["error"] = False
        context["error_message"] = "Артикул не найден!"
    return render(request, "apps/seo-group-result.html", context)


def seo_group_search(request):
    logged_in_user = request.user
    context = {"objects": []}
    wrong_link = False

    if wrong_link:
        context["error"] = False
        context["error_message"] = "Артикул не найден!"
    return render(request, "apps/seo-group-search.html", context)


def selection_requests(request):
    logged_in_user = request.user
    context = {"objects": []}
    wrong_link = False
    if request.method == "POST":
        phrase = request.POST["phrase"]
        context["objects"] = get_phrases(phrase)
        if wrong_link:
            context["error"] = False
            context["error_message"] = "Артикул не найден!"
        print(f"SGDHJKFGSDHGFH {context}")
        return JsonResponse(context, safe=True)
    return render(request, "apps/selection-requests.html", context)


def product_card_search(request):
    logged_in_user = request.user
    context = {"objects": []}
    wrong_link = False

    if wrong_link:
        context["error"] = False
        context["error_message"] = "Артикул не найден!"

    return render(request, "apps/product-card-search.html", context)


def frequency(request):
    if request.method == "POST":
        phrases = json.loads(request.body)["phrases"]
        context = get_frequency(phrases)
    return JsonResponse(context, safe=True)
