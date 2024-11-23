import datetime

from apps.home.helper import Helper
from apps.home.models import ClientPhrase, ClientProduct, Phrase
from apps.home.services.elastic import ES


def indexExists(list, index):
    if 0 <= index < len(list):
        return True
    else:
        return False


def get_group_search(context, groupA, groupB):
    date_yesterday = datetime.datetime.today() - datetime.timedelta(1)
    date_yesterday = datetime.datetime.strftime(date_yesterday, "%Y-%m-%d")
    phrases_A = []
    phrases_B = []
    context.update({"groupA": []})
    context.update({"groupB": []})
    context.update({"A": []})
    context.update({"B": []})
    context.update({"A_B": []})
    context.update({"AminusB": []})
    context.update({"BminusA": []})

    es = ES()

    for a in groupA:
        context["groupA"].append(Helper.check_sku(a, 1, "seo"))
        position_history = es.get_doc_by_sku(a, type="last")

        for p in position_history:  # TODO remove this after clean db
            p["phrase"] = p["phrase"].replace("'", "")

        if position_history:
            for phrase in position_history:
                if (
                    phrase["phrase"] not in phrases_A
                    and phrase["date"] == date_yesterday
                ):
                    phrases_A.append(phrase["phrase"])

    for b in groupB:
        context["groupB"].append(Helper.check_sku(b, 1, "seo"))
        position_history = es.get_doc_by_sku(b)

        for p in position_history:  # TODO remove this after clean db
            p["phrase"] = p["phrase"].replace("'", "")

        if position_history:
            for phrase in position_history:
                if (
                    phrase["phrase"] not in phrases_B
                    and phrase["date"] == date_yesterday
                ):
                    phrases_B.append(phrase["phrase"])

    context.update({"HUINYA": []})

    if len(context["groupA"]) > len(context["groupB"]):
        for i, phrase in enumerate(context["groupA"]):
            context["HUINYA"].append(
                {
                    "image1": phrase["cover"],
                    "name1": phrase["title"],
                    "image2": context["groupB"][i]["cover"]
                    if indexExists(context["groupB"], i)
                    else "",
                    "name2": context["groupB"][i]["title"]
                    if indexExists(context["groupB"], i)
                    else "",
                }
            )
    else:
        for i, phrase in enumerate(context["groupB"]):
            context["HUINYA"].append(
                {
                    "image1": context["groupA"][i]["cover"]
                    if indexExists(context["groupA"], i)
                    else "",
                    "name1": context["groupA"][i]["title"]
                    if indexExists(context["groupA"], i)
                    else "",
                    "image2": phrase["cover"],
                    "name2": phrase["title"],
                }
            )
    print(f"HUINYA is {context['HUINYA']}")
    phrase_pg_A = Phrase.objects.filter(value__in=phrases_A)
    phrase_pg_B = Phrase.objects.filter(value__in=phrases_B)

    for phrase in phrases_A:
        is_ph = False
        for ph in phrase_pg_A:
            if phrase == ph.value:
                context["A"].append(({"phrase": ph.value, "frequency": ph.frequency}))
                is_ph = True
        if not is_ph:
            context["A"].append({"phrase": phrase, "frequency": 0})

    for phrase in phrases_B:
        is_ph = False
        for ph in phrase_pg_B:
            if phrase == ph.value:
                context["B"].append(({"phrase": ph.value, "frequency": ph.frequency}))
                is_ph = True
        if not is_ph:
            context["B"].append({"phrase": phrase, "frequency": 0})

    for phrase in context["B"]:
        for ph in context["A"]:
            if phrase == ph:
                context["A_B"].append(phrase)
    context.update({"circleA": len(context["A"])})
    context.update({"circleB": len(context["B"])})
    context.update({"circleAB": len(context["A_B"])})
    # print(f"A is {context['A']}")
    # print(f"B is {context['B']}")
    # print(f"phrase_pg {phrase_pg_A}")
    # print(f"phrase_pg {phrase_pg_B}")
    for phrase in context["A"]:
        if phrase not in context["B"]:
            context["AminusB"].append(phrase)

    for phrase in context["B"]:
        if phrase not in context["A"]:
            context["BminusA"].append(phrase)

    return context
