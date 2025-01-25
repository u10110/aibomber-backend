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
from apps.telegram.sndr import MessageProcessor
import traceback

TELETHON_HOST = config("TELETHON_HOST")

from django.utils.decorators import method_decorator
from django_telegram_login.authentication import verify_telegram_authentication
from django.middleware.csrf import get_token


def send_to_gpt(request):
    """
    Обрабатывает запросы чата на этапе создания проекта.
    """
    if request.method == "POST":
        try:
            # Парсим данные формы
            data = json.loads(request.body.decode("utf-8"))
            logger.debug(data)
            project = Project(
                id=None,
                title=data.get("title"),
                agent_type=data.get("agent_type"),
                work_option=int(data.get("work_option")),
                gpt_version=int(data.get("gpt_version")),
                knowledge_base_text=data.get("knowledge_base_text"),
                hello_text=data.get("hello_text"),
                prompt=data.get("prompt"),
            )

            # Форматируем историю чата
            chat = data.get("chat_history", [])
            formatted_history = []
            chat_history = chat[:-1]
            question = chat[:1]
            # Форматируем историю чата
            for item in chat_history:
                logger.debug(item)
                if item.get('bot'):
                    formatted_history.append({"role": "assistant", "content": item.get('message')})
                else:
                    formatted_history.append({"role": "user", "content": item.get('message')})

            # Ограничиваем длину истории (например, 10 пар сообщений)
            formatted_history = formatted_history[-20:]  # 10 вопросов и 10 ответов
            logger.debug(formatted_history)
            # Инициализируем GPTAssistant с историей чата
            assistant = GPTAssistant(project)
            # Передаём историю в GPTAssistant
            assistant.chat_history = formatted_history

            # Получаем вопрос
            question = question[0].get('message', False)
            if not question:
                return JsonResponse({"error": "Вопрос не предоставлен."}, status=400)
            logger.debug(question)
            # Получаем ответ от GPT
            response = assistant.ask_question(question, False)

            return JsonResponse({
                "question": question,
                "response": response
            }, status=200)
        except Exception as e:
            logger.error(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Метод не поддерживается."}, status=405)


def send_chat_messages(request, chat_id):
    if not chat_id:
        return HttpResponse(status=404)
    if request.method == 'POST':

        data = json.loads(request.body.decode("utf-8"))
        message = data.get('message')
        logger.debug(message)
        current_chat = Chat.objects.filter(
            id=chat_id,
            project__in=Project.objects.filter(client_id=request.user.id)
        ).first()

        current_channel = Channel.objects.filter(id=current_chat.channel_id).first()

        message_processor = MessageProcessor()

        sent = message_processor.send_message_to_telegram(
            current_channel.phone,
            current_chat.user_id,
            message)
        logger.info(sent)
        if sent == 'SENT':
            new_message = ChatMessages.objects.create(
                chat_id=current_chat,
                user_name=current_channel.phone,
                user_message=message[:555],
                message_type="outcoming"
            )
            current_channel.remaining_messages = F('remaining_messages') - 1
            current_channel.save()

            return JsonResponse({
                'msg':
                    {
                        'message': new_message.user_message,
                        'time': new_message.created_at.isoformat(),
                        'senderId': current_chat.user_id,
                        'user_name': new_message.user_name,
                        'message_type': new_message.message_type,
                        'feedback': {
                            'isSent': True,
                            'isDelivered': True,
                            'isSeen': True
                        },
                    }, 'chat': {
                    'id': current_chat.id,
                    'lastMessage': {
                        'message': new_message.user_message,
                        'time': new_message.created_at.isoformat(),
                        'feedback': {
                            'isSent': True,
                            'isDelivered': True,
                            'isSeen': True
                        },
                    },
                    'status': current_chat.status,
                    'is_auto_active': current_chat.is_auto_active,
                    'channel_id': current_chat.channel_id,
                }
            }, safe=False)

        if sent == 'USER_DOESNT_EXIST':
            current_chat.status = 'user_doesnt_exist'
            current_chat.last_message_time = datetime.datetime.now(tz=timezone.utc)
            current_chat.save()
            logger.info(f"user_doesnt_exist {current_chat.user_id} ")
            return JsonResponse({'success': False, 'error': 'Пользователь не найден '}, safe=False)

        if sent == 'SENT_ERROR':
            logger.info(f"Ошибка отправки {current_chat.user_id} ")
            return JsonResponse({'success': False, 'error': 'Ошибка отправки '}, safe=False)


def chat_messages(request, chat_id):
    if not chat_id:
        return HttpResponse(status=404)

    current_chat = Chat.objects.filter(
        id=chat_id,
        project__in=Project.objects.filter(client_id=request.user.id)
    ).first()

    current_messages = []

    if current_chat:
        current_messages = ChatMessages.objects.filter(
            chat_id=chat_id,
        ).order_by('created_at')

    messages_data = []
    for message in current_messages:
        messages_data.append({
            'message': message.user_message,
            'time': message.created_at.isoformat(),
            'senderId': current_chat.user_id,
            'user_name': message.user_name,
            'message_type': message.message_type,
            'feedback': {
                'isSent': True,
                'isDelivered': True,
                'isSeen': True
            },
        })

    last_messages = ChatMessages.objects.filter(chat_id=current_chat).values(
        'message_type',
        'user_name',
        'user_message',
        'created_at'
    ).order_by('-created_at').first()

    chat_data = {
        'id': current_chat.id,
        'lastMessage': {
            'message': last_messages.get('user_message'),
            'time': last_messages.get('created_at').isoformat(),
            'feedback': {
                'isSent': True,
                'isDelivered': True,
                'isSeen': True
            },
        },
        'status': current_chat.status,
        'is_auto_active': current_chat.is_auto_active,
        'channel_id': current_chat.channel_id,
        'messages': messages_data,
    }

    return JsonResponse({
        'chat': chat_data,
        'contact': {
            'fullName': current_chat.user_name,
            'role': current_chat.user_id,
            'about': last_messages.get('user_message'),
            'avatar': '',
            'id': current_chat.user_id,
        }
    }, safe=False)


def chats(request):
    statuses = request.GET.get("status", '')
    project = request.GET.get("project", '')
    projects_filter = Project.objects.filter(client=request.user)

    if len(project) > 0:
        projects_filter = projects_filter.filter(id__in=project.split(','))

    chats_list = Chat.objects.filter(
        project_id__in=projects_filter)
    if len(statuses) > 0:
        chats_list = chats_list.filter(status__in=statuses.split(','))

    chat_contacts = []
    contacts = []
    for chat in chats_list:
        last_messages = ChatMessages.objects.filter(chat_id=chat).values(
            'message_type',
            'user_name',
            'user_message',
            'created_at'
        ).order_by('-created_at').first()
        chat_contacts.append({
            'id': chat.id,
            'lastMessage': {
                'message': last_messages.get('user_message'),
                'time': last_messages.get('created_at').isoformat(),
                'feedback': {
                    'isSent': True,
                    'isDelivered': True,
                    'isSeen': True
                },
            },
            'fullName': chat.user_name,
            'role': chat.user_id,
            'avatar': '',
            'about': last_messages.get('user_message'),
            'status': chat.status,
            'is_auto_active': chat.is_auto_active,
            'channel_id': chat.channel_id,
            'project_id': chat.project_id
        })
        contacts.append({
            'id': chat.user_id,
            'fullName': chat.user_name,
            'role': chat.user_id,
            'avatar': '',
            'about': last_messages.get('user_message'),
        })

    return JsonResponse({'chatsContacts': chat_contacts, 'contacts': contacts}, safe=False)


def project_delete(request, project_id):
    user = request.user
    project_to_delete = Recipient.objects.filter(id=project_id, client=user).get()
    if not project_to_delete:
        return HttpResponse(status=404)
    else:
        project_to_delete.delete()
        return HttpResponse(status=200)


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


def project_create(request):
    return project_get_or_save(request, None)


def project_get_or_save(request, project_id):
    user = request.user

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
                project_to_save = Project.objects.filter(id=project_id, client=user).get()

            if not project_to_save:
                return HttpResponse(status=404)

            project_to_save.title = data.get('name', '')
            project_to_save.agent_type = data.get('agent_type', None)
            project_to_save.work_option = data.get('work_option', 1)
            project_to_save.gpt_version = data.get('gpt_version', 1)
            project_to_save.prompt = data.get('promptText')
            project_to_save.hello_text = data.get('hello_text')

            # project_to_save.outgoing_limit = request.POST.get('', 10)
            project_to_save.per_conversation_limit = data.get('limitForOneChat', 10)
            project_to_save.message_limit = data.get('limitForDay', 10)

            project_to_save.time_end = data.get('timeStart')
            project_to_save.time_start = data.get('timeEnd')
            project_to_save.knowledge_base_text = data.get('knownBaseText')

            project_to_save.integrations = data.get('knownBaseText')

            project_to_save.save()

            # Обработка каналов
            new_channels = data.get('channels', [])
            if project_id is None:  # Если это редактирование существующего проекта
                new_channels_set = set(Channel.objects.filter(id__in=[c for c in new_channels]))
                Channel.objects.filter(id__in=[c.id for c in new_channels_set]).update(project_id=project_to_save.id)
            else:
                new_channels_set = set(Channel.objects.filter(id__in=[c for c in new_channels]))
                # Для нового проекта просто привязываем все выбранные каналы

                # Получаем текущие каналы проекта
                current_channels = set(Channel.objects.filter(project_id=project_to_save.id))

                # Находим каналы, которые нужно освободить (убрать project_id)
                channels_to_free = current_channels - new_channels_set
                Channel.objects.filter(id__in=[c.id for c in channels_to_free]).update(project_id=None)

                # Находим новые каналы, которые нужно привязать
                channels_to_assign = new_channels_set - current_channels
                Channel.objects.filter(id__in=[c.id for c in channels_to_assign]).update(project_id=project_to_save.id)

            # Обработка пайплайнов
            # pipelines = data.get('pipelines', [])

            # CrmPipelines.objects.filter(project_id=project_to_save.id).delete()
            # crm_pipelines = [
            #    CrmPipelines(
            #        project_id=project_to_save.id,
            ##        remote_name=pipeline['remote_name'],
            #        remote_step_id=pipeline['remote_step_id'],
            #        remote_pipeline_id=pipeline['remote_pipeline_id'],
            #        trigger=pipeline['trigger']
            #    ) for pipeline in pipelines
            # ]
            # CrmPipelines.objects.bulk_create(crm_pipelines)

            # Обновляем project_id для связанных каналов
            # channels = data.get('channel', [])
            # for channel in channels:
            #    channel.project_id = project_to_save.id
            #    channel.save()

            # for file_form in file_formset:
            #    if file_form.cleaned_data.get('file'):
            #        project_file = file_form.save(commit=False)
            #       project_file.project = project
            #        project_file.save()
            return JsonResponse({'success': True, 'created': True}, safe=False)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error("project save error")
            return HttpResponse(status=500)
    else:
        if project_id:
            project = Project.objects.filter(
                id=project_id,
                client_id=request.user.id
            ).first()

            channel_list = Channel.objects.filter(project_id=project.id)

            channels_data = []
            for channel in channel_list:
                channels_data.append({
                    'title': channel.title,
                    'id': channel.id,
                })

            files_list = ProjectFile.objects.filter(project_id=project.id)

            files_data = []
            for file in files_list:
                files_data.append({
                    'title': file.title,
                    'id': file.id,
                })

            project_data = {
                'name': project.title,
                'workOption': project.work_option,
                'gptVersion': project.gpt_version,
                'limitForOneChat': project.per_conversation_limit,
                'limitForDay': project.message_limit,
                'timeStart': project.time_start,
                'timeEnd': project.time_end,
                'helloMessage': project.hello_text,
                'promptText': project.prompt,
                'knownBaseText': project.knowledge_base_text,
                'knownBaseFiles': files_data,
                'channels': channels_data
            }
            return JsonResponse(project_data, safe=False)
        else:
            return HttpResponse(status=404)


def recipient_create(request):
    return recipient_get_or_save(request, None)


def recipient_get_or_save(request, recipient_id):
    user = request.user

    if request.method == 'POST':
        data = json.loads(request.body.decode("utf-8"))

        try:
            if recipient_id is None:
                recipient_to_save = Recipient(
                    client=user
                )
            else:
                recipient_to_save = Recipient.objects.filter(id=recipient_id, client=user).get()

            if not recipient_to_save:
                return HttpResponse(status=404)

            recipient_to_save.title = data.get('name')
            recipient_to_save.project_id = data.get('project')

            recipient_to_save.remote_ids = data.get('mailingData')
            recipient_to_save.start_date = data.get('date')

            recipient_to_save.save()
            return JsonResponse({'success': True, 'created': True}, safe=False)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error("recipient save error")
            return HttpResponse(status=500)
    else:
        if recipient_id:
            recipient = Recipient.objects.filter(
                id=recipient_id,
                client_id=request.user.id
            ).first()

            if recipient:

                recipient_data = {
                    'name': recipient.title,
                    'project': recipient.project_id,
                    'mailingData': recipient.remote_ids,
                    'date': recipient.start_date,
                    'isDate': recipient.start_date is not None,
                }

                return JsonResponse(recipient_data, safe=False)
            else:
                return HttpResponse(status=404)


def recipient_delete(request, recipient_id):
    user = request.user
    recipient_to_delete = Recipient.objects.filter(id=recipient_id, client=user).get()
    if not recipient_to_delete:
        return HttpResponse(status=404)
    else:
        recipient_to_delete.delete()
        return HttpResponse(status=200)


def recipients(request):
    recipient_list = Recipient.objects.filter(client=request.user).values(
        'title',
        'work_option',
        'status',
        'remote_ids',
        'id')

    data = list(recipient_list)
    return JsonResponse(data, safe=False)


def channel_create(request):
    return channel_get_or_save(request, None)


def channel_get_or_save(request, channel_id):
    user = request.user

    if request.method == 'POST':
        data = json.loads(request.body.decode("utf-8"))

        try:
            if channel_id is None:
                channel_to_save = Channel(
                    client=user,
                    is_active=False
                )
            else:
                channel_to_save = Channel.objects.filter(id=channel_id, client=user).get()

            if not channel_to_save:
                return HttpResponse(status=404)

            phone_number = re.sub(r'[^\d+]', '', data.get('phone').strip())
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number

            channel_to_save.title = data.get('name')
            channel_to_save.source = data.get('source')
            channel_to_save.phone = phone_number

            channel_to_save.save()
            return JsonResponse({'success': True, 'created': True}, safe=False)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error("recipient save error")
            return HttpResponse(status=500)
    else:
        if channel_id:
            channel = Channel.objects.filter(
                id=channel_id,
                client_id=request.user.id
            ).first()

            if channel:

                channel_data = {
                    'name': channel.title,
                    'source': channel.source,
                    'phone': channel.phone
                }

                return JsonResponse(channel_data, safe=False)
            else:
                return HttpResponse(status=404)


def channel_delete(request, channel_id):
    user = request.user
    channel_to_delete = Channel.objects.filter(id=channel_id, client=user).get()
    if not channel_to_delete:
        return HttpResponse(status=404)
    else:
        channel_to_delete.delete()
        return HttpResponse(status=200)


def channels(request):
    channel_list = Channel.objects.filter(client=request.user)

    data = []
    for channel in channel_list:
        project = Project.objects.filter(id=channel.project_id).first()
        project_title = ''
        if project :
            project_title=project.title

        data.append({
            'title': channel.title,
            'status': channel.status,
            'phone': channel.phone,
            'max_daily_messages': channel.max_daily_messages,
            'id': channel.id,
            'remaining_messages': channel.remaining_messages,
            'is_active': channel.is_active,
            'source': channel.source,
            'project_title': project_title
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
