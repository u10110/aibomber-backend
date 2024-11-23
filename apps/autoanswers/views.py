# Create your views here.
import datetime
import json
from http import client

from django.db.models import Count, Q, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from .models import *

# from apps.billing.models import Limits, Order
# from apps.home.models import *
# from apps.home.WB_token import X64ApiClient


def create_autoanswers(request):
    context = {}
    return render(request, "apps/create-autoanswers.html", context)
