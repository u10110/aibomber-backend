
import string
from decouple import config
from sqlite3 import IntegrityError

from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.files.storage import FileSystemStorage
from django.db.utils import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template import loader
from django.urls import path, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DeleteView
from loguru import logger
from lxml import html
from sentry_sdk import last_event_id
import re

from apps.alert.views import billing_check
from apps.authentication.models import UserInfo
from apps.billing.helper import Helper as BHelper
from apps.billing.models import Limits, Order, Paid, UnicTariff
from apps.users_control.models import ReferalCounter, UsersAgreement
from core.settings import MEDIA_ROOT


from apps.telegram.sndr import ProjectProcessor
from apps.telegram.prsr import process_project

from .forms import *
from .helper import Helper
from .models import (
    ReferralClickCounter,
    ReferralUsers,
    ReferralLinks,
    ClientSettings,
    Channel,
    Chat,
    Phone,
    ChatMessages,
    User
)
from .module import *
from .services.services import MinioService
from django.shortcuts import get_object_or_404
from django.db.models import Max, OuterRef, Subquery, Count, Q, F
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

from django.shortcuts import render
from django.http import JsonResponse
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from django.core import serializers
from .models import Project
from .services.gpt_assistant import GPTAssistant
from django.db.models import Count, Max, Subquery, OuterRef, IntegerField, Case, When
import random
from django.contrib.auth import authenticate, get_user_model, login
from django.http import JsonResponse

TELETHON_HOST = config("TELETHON_HOST")

from django.utils.decorators import method_decorator

from django_telegram_login.authentication import verify_telegram_authentication
from django.middleware.csrf import get_token




def projects(request):

    projects_list = Project.objects.filter(client=request.user).values(
        'title',
        'work_option',
        'agent_type',
        'status',
        'is_active',
        'id')

    data = list(projects_list)
    return JsonResponse(data, safe=False)


def is_ajax(request):
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"

@csrf_exempt
def auth_login(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        phone = data.get("phone")
        password = data.get("password")
        phone = (
            phone.replace("(", "")
                .replace(")", "")
                .replace("-", "")
                .replace(" ", "")
        )
        if phone.startswith("8"):
            phone = "+7" + phone[1:]
        user = authenticate(phone=phone, password=password)
        logger.debug(user)
        if (
                not User.objects.filter(phone=phone).exists()
                or User.objects.get(phone=phone).is_active == False
        ):
            return JsonResponse({"error": "not_reg"}, status=400)
        if (user is not None) and user.is_active:
            login(request, user)
            session_user = {
                'phone': user.phone,
                'username': user.username
            }
            return JsonResponse({"accessToken": get_token(request), "userData": json.dumps(session_user)}, status=200)
        else:
            msg = "Invalid credentials"
            return JsonResponse({"error": msg}, status=400)
    else:
        return HttpResponse(status=404)


