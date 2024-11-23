import json

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views import View

from .services.amo import Deal


def test(request):
    if request.method == "POST":
        print(f"asfasf {request.body}")
        data = json.loads(request.body)
        print(f"asfasf {data}")
        client_id = data["client_id"]
        type_deal = data["type_deal"]
        d = Deal(client_id, type_deal)
        resp = d.save()
        return JsonResponse(resp, status=200)
