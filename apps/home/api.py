
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
import traceback
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
    print(data)
    return JsonResponse(data, safe=False)


def project_save(request):
    user = request.user
    project_id = request.POST.get('project_id', None)

    if request.method == 'POST':
        data = json.loads(request.body.decode("utf-8"))

        try:
            if project_id is None:
                project_to_save = Project(
                    status='new',
                    client=user,
                    is_active=False
                )
            else:
                project_to_save = data.get(id=project_id)

            project_to_save.title = data.get('name', '')
            project_to_save.agent_type = data.get('agent_type', None)
            project_to_save.work_option = data.get('work_option', 1)
            project_to_save.gpt_version = data.get('gpt_version', 1)
            project_to_save.prompt = data.get('promptText')
            project_to_save.hello_text = data.get('hello_text')

            #project_to_save.outgoing_limit = request.POST.get('', 10)
            project_to_save.per_conversation_limit = data.get('limitForOneChat', 10)
            project_to_save.message_limit = data.get('limitForDay', 10)

            project_to_save.time_end = data.get('timeStart')
            project_to_save.time_start = data.get('timeEnd')
            project_to_save.knowledge_base_text = data.get('knownBaseText')

            project_to_save.integrations = data.get('knownBaseText')

            project_to_save.save()

            # Обработка каналов
            new_channels = data.get('channel', [])
            if not project_id:  # Если это редактирование существующего проекта
                Channel.objects.filter(id__in=[c.id for c in new_channels]).update(project_id=project_to_save.id)
            else:
                # Для нового проекта просто привязываем все выбранные каналы

                # Получаем текущие каналы проекта
                current_channels = set(Channel.objects.filter(project_id=project_to_save.id))

                # Находим каналы, которые нужно освободить (убрать project_id)
                channels_to_free = current_channels - new_channels
                Channel.objects.filter(id__in=[c.id for c in channels_to_free]).update(project_id=None)

                # Находим новые каналы, которые нужно привязать
                channels_to_assign = new_channels - current_channels
                Channel.objects.filter(id__in=[c.id for c in channels_to_assign]).update(project_id=project_to_save.id)

            # Аналогичная обработка для получателей
            new_recipients = data.get('recipients', [])

            if not project_id:
                Recipient.objects.filter(id__in=[r.id for r in new_recipients]).update(project_id=project_to_save.id)
            else:
                # Для нового проекта привязываем всех выбранных получателей

                current_recipients = set(Recipient.objects.filter(project_id=project_to_save.id))

                # Освобождаем старых получателей
                recipients_to_free = current_recipients - new_recipients
                Recipient.objects.filter(id__in=[r.id for r in recipients_to_free]).update(project_id=None)

                # Привязываем новых получателей
                recipients_to_assign = new_recipients - current_recipients
                Recipient.objects.filter(id__in=[r.id for r in recipients_to_assign]).update(project_id=project_to_save.id)

            # Обработка пайплайнов
            pipelines = data.get('pipelines', [])

            CrmPipelines.objects.filter(project_id=project_to_save.id).delete()
            crm_pipelines = [
                CrmPipelines(
                    project_id=project_to_save.id,
                    remote_name=pipeline['remote_name'],
                    remote_step_id=pipeline['remote_step_id'],
                    remote_pipeline_id=pipeline['remote_pipeline_id'],
                    trigger=pipeline['trigger']
                ) for pipeline in pipelines
            ]
            CrmPipelines.objects.bulk_create(crm_pipelines)


            # Обновляем project_id для связанных каналов
            channels = data.get('channel', [])
            for channel in channels:
                channel.project_id = project_to_save.id
                channel.save()

                # Обновляем project_id для связанных получателей
                # Обновляем project_id для связанных получателей
            recipients = data.get('recipients', [])

            for recipient in recipients:
                recipient.project_id = project_to_save.id
                recipient.save()

            #for file_form in file_formset:
            #    if file_form.cleaned_data.get('file'):
            #        project_file = file_form.save(commit=False)
            #       project_file.project = project
            #        project_file.save()
            return JsonResponse({'success': True}, safe=False)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error("project save error")
            return HttpResponse(status=500)

    return HttpResponse(status=404)


def recipients(request):

    recipient_list = Recipient.objects.filter(project_id__in=Project.objects.filter(client=request.user)).values(
        'title',
        'work_option',
        'status',
        'remote_ids',
        'id')

    data = list(recipient_list)
    return JsonResponse(data, safe=False)


def channels(request):

    channel_list = Channel.objects.filter(project_id__in=Project.objects.filter(client=request.user))

    data = []
    for channel in channel_list:

        project = Project.objects.filter(id=channel.project_id).first()
        data.append({
            'title': channel.title,
            'status': channel.status,
            'phone': channel.phone,
            'max_daily_messages': channel.max_daily_messages,
            'id': channel.id,
            'remaining_messages': channel.remaining_messages,
            'is_active': channel.is_active,
            'source': channel.source,
            'project_title': project.title
        })

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
                'username': user.username,
                'user_id': user.id
            }
            return JsonResponse({"accessToken": get_token(request), "userData": json.dumps(session_user)}, status=200)
        else:
            msg = "Invalid credentials"
            return JsonResponse({"error": msg}, status=400)
    else:
        return HttpResponse(status=404)


