from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from apps.alert.services.wb_api import WbAPI
from apps.home.helper import Helper
from apps.home.services.elastic import ES


def get_product_card(context, sku):
    wb_api = WbAPI()
    product = wb_api.get_item_characters(sku)
    if not product:
        return {"error": "sku not found"}
    context.update(product)
    context.update(Helper.check_sku(sku, 1, "seo"))
    all_phrases = []
    es = ES()
    position_history = es.get_doc_by_sku(sku)
    if position_history:

        for p in position_history:  # TODO remove this after clean db
            p["phrase"] = p["phrase"].replace("'", "")

        import re

        for phrase in position_history:
            check = re.sub(r"[^a-zA-Z0-9]", "|", phrase["phrase"])
            if phrase["phrase"] not in all_phrases and len(check) > 4:
                all_phrases.append(phrase["phrase"])
        context.update({"all_phrases": all_phrases})
    else:
        context.update({"all_phrases": []})
    context.update({"sku": sku})
    # context["sku"] = sku
    # context["title"] = item["imt_name"]
    # context["vendor"] = item["vendor_code"]
    # context["description"] = item["description"]
    # for option in item['grouped_options']:

    return context
