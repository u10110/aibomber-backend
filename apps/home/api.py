import string
from decouple import config
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from loguru import logger

import re
import urllib
import os

import uuid
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
from .models import Project
from .services.gpt_assistant import GPTAssistant

from django.contrib.auth import authenticate, get_user_model, login
from django.http import JsonResponse
from apps.telegram.sndr import MessageProcessor
import traceback

TELETHON_HOST = config("TELETHON_HOST")
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
            # files=data.get("knownBaseFiles")
            # f files:
            #    for project_file in files:
            #        project.knowledge_base_text+= '\r' + project_file.get('name')

            # Форматируем историю чата
            chat = data.get("chat_history", [])
            formatted_history = []
            question = ''
            # Форматируем историю чата
            for item in chat:
                if item.get('bot'):
                    formatted_history.append({"role": "assistant", "content": item.get('message')})
                else:
                    formatted_history.append({"role": "user", "content": item.get('message')})
                    question = item.get('message')

            # Ограничиваем длину истории (например, 10 пар сообщений)
            formatted_history = formatted_history[-20:]  # 10 вопросов и 10 ответов

            # Инициализируем GPTAssistant с историей чата
            assistant = GPTAssistant(project)
            # Передаём историю в GPTAssistant
            assistant.chat_history = formatted_history[:-1]

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
        try:
            data = json.loads(request.body.decode("utf-8"))
            message = data.get('message')
            logger.debug(message)
            current_chat = Chat.objects.filter(
                id=chat_id,
                project__in=Project.objects.filter(client_id=request.user.id),
                is_auto_active=False
            ).first()

            if current_chat:

                current_channel = Channel.objects.filter(id=current_chat.channel_id, status='authorized').first()

                if current_channel:

                    new_message = ChatMessages.objects.create(
                        chat_id=current_chat,
                        user_message=message[:555],
                        message_type="outcoming",
                        remote_status="sent"
                    )

                    message_processor = MessageProcessor()

                    response = message_processor.send_message_to_telegram(
                        current_channel.phone,
                        current_chat.user_id,
                        message)
                    response_body = json.loads(response.content)
                    if response and response.status_code == 200:

                        remote_message_entity = response_body.get('result')
                        if not current_chat.remote_chat_id:
                            current_chat.remote_chat_id = remote_message_entity.get('sender_id')
                            current_chat.save()

                        new_message.remote_status = 'deliver'
                        new_message.remote_id = remote_message_entity.get('id')
                        new_message.remote_message = remote_message_entity
                        new_message.save()

                        return JsonResponse({
                            'success': True,
                            'msg':
                                {
                                    'message': new_message.user_message,
                                    'time': new_message.created_at.isoformat(),
                                    'senderId': current_chat.user_id,
                                    'user_name': current_chat.user_name,
                                    'message_type': new_message.message_type,
                                    'feedback': {
                                        'isSent': True,
                                        'isDelivered': True,
                                        'isSeen': True
                                    },
                                }
                        }, safe=False)

                    if response and response.status_code == 404:
                        new_message.remote_status = 'user_doesnt_exist'
                        new_message.save()
                        current_chat.status = 'user_doesnt_exist'
                        current_chat.last_message_time = datetime.datetime.now(tz=datetime.timezone.utc)
                        current_chat.save()
                        logger.info(f"user_doesnt_exist {current_chat.user_id} ")
                        return JsonResponse({'success': False, 'error': 'Пользователь не найден '}, safe=False)

                    if response and response.status_code == 500:
                        logger.debug(response_body)
                        logger.info(f"Ошибка отправки {current_chat.user_id} ")
                        current_chat.status = response_body.get('detail')
                        current_chat.save()
                        new_message.remote_status = response_body.get('detail')
                        new_message.save()
                        return JsonResponse({'success': False, 'error': response_body.get('detail')}, safe=False)

                return JsonResponse({'success': False, 'error': 'Канал для отправки не авторизован '}, safe=False)

        except Exception as e:
            logger.error(traceback.format_exc())
            return JsonResponse({"error": str(e)}, status=500)

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
            'user_name': current_chat.user_name,
            'message_type': message.message_type,
            'feedback': {
                'isSent': True,
                'isDelivered': True,
                'isSeen': True
            },
        })

    last_messages = ChatMessages.objects.filter(chat_id=current_chat).values(
        'message_type',
        'user_message',
        'created_at'
    ).order_by('-created_at').first()

    last_message = {}
    last_user_message = ''
    if last_messages:
        last_message = {
            'message': last_messages.get('user_message'),
            'time': last_messages.get('created_at').isoformat(),
            'feedback': {
                'isSent': True,
                'isDelivered': True,
                'isSeen': True
            },
        }
        last_user_message = last_messages.get('user_message')

    chat_data = {
        'id': current_chat.id,
        'lastMessage': last_message,
        'status': current_chat.status,
        'is_auto_active': current_chat.is_auto_active,
        'channel_id': current_chat.channel_id,
        'messages': messages_data,
    }
    user_name = current_chat.user_name
    if len(current_chat.user_name) == 0:
        user_name = current_chat.user_id

    return JsonResponse({
        'chat': chat_data,
        'contact': {
            'fullName': user_name,
            'role': current_chat.user_id,
            'about': last_user_message,
            'avatar': '',
            'status': current_chat.status,
            'id': current_chat.id,
        }
    }, safe=False)


def chats(request):
    statuses = request.GET.get("status", '')
    project = request.GET.get("project", '')
    recipients = request.GET.get("recipients", '')
    channels = request.GET.get("channels", '')

    projects_filter = Project.objects.filter(client=request.user)
    recipients_filter = Recipient.objects.filter(client=request.user)
    channels_filter = Channel.objects.filter(client=request.user)

    if len(project) > 0:
        projects_filter = projects_filter.filter(id__in=project.split(','))

    if len(recipients) > 0:
        recipients_filter = recipients_filter.filter(id__in=recipients.split(','))

    if len(channels) > 0:
        channels_filter = channels_filter.filter(id__in=channels.split(','))

    chats_list = Chat.objects.filter(
        project_id__in=projects_filter)
    if len(statuses) > 0:
        chats_list = chats_list.filter(status__in=statuses.split(','))

    if len(recipients) > 0:
        chats_list = chats_list.filter(recipient_id__in=recipients_filter)

    if len(channels) > 0:
        chats_list = chats_list.filter(channel__in=channels_filter)

    chat_contacts = []
    contacts = []
    for chat in chats_list:
        last_messages = ChatMessages.objects.filter(chat_id=chat).values(
            'message_type',
            'user_message',
            'created_at'
        ).order_by('-created_at').first()

        last_message = {}
        last_user_message = ''
        if last_messages:
            last_message = {
                'message': last_messages.get('user_message'),
                'time': last_messages.get('created_at').isoformat(),
                'feedback': {
                    'isSent': True,
                    'isDelivered': True,
                    'isSeen': True
                },
            }
            last_user_message = last_messages.get('user_message')

        user_name = chat.user_name
        if len(chat.user_name) == 0:
            user_name = chat.user_id

        chat_contacts.append({
            'id': chat.id,
            'lastMessage': last_message,
            'fullName': user_name,
            'role': chat.user_id,
            'avatar': '',
            'about': last_user_message,
            'status': chat.status,
            'is_auto_active': chat.is_auto_active,
            'channel_id': chat.channel_id,
            'project_id': chat.project_id
        })
        contacts.append({
            'id': chat.id,
            'fullName': user_name,
            'role': chat.user_id,
            'avatar': '',
            'status': chat.status,
            'about': last_user_message,
        })

    return JsonResponse({'chatsContacts': chat_contacts, 'contacts': contacts}, safe=False)


def chats_export(request):
    projects_filter = Project.objects.filter(client=request.user)

    chats_list = Chat.objects.filter(
        project_id__in=projects_filter)

    chats = []
    for chat in chats_list:
        project = Project.objects.filter(id=chat.project_id).first()
        project_title = ''

        if project:
            project_title = project.title

        chats.append({
            'id': chat.id,
            'fullName': chat.user_name,
            'user_id': chat.user_id,
            'status': chat.status,
            'is_auto_active': chat.is_auto_active,
            'phone': chat.phone,
            'channel_id': chat.channel_id,
            'project_id': chat.project_id,
            'last_message_time': chat.last_message_time,
            'project_title': project_title
        })

    return JsonResponse({'chats': chats}, safe=False)


def project_delete(request, project_id):
    user = request.user
    try:
        project_to_delete = Project.objects.filter(id=project_id, client=user).get()
        project_to_delete.delete()
        return HttpResponse(status=200)
    except Project.DoesNotExist:
        return HttpResponse(status=404)


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
            project_to_save.hello_text = data.get('helloMessage')

            # project_to_save.outgoing_limit = request.POST.get('', 10)
            project_to_save.per_conversation_limit = data.get('limitForOneChat', 10)
            project_to_save.outgoing_limit = data.get('limitForDay', 10)

            project_to_save.time_end = data.get('timeEnd')
            project_to_save.time_start = data.get('timeStart')
            project_to_save.knowledge_base_text = data.get('knownBaseText')

            project_to_save.integrations = data.get('integrations', '')

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

            #Обработка пайплайнов
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

            #Обновляем project_id для связанных каналов
            channels = data.get('channel', [])
            for channel in channels:
                channel.project_id = project_to_save.id
                channel.save()
            new_files = data.get('knownBaseFiles', [])
            not_in_delete = []
            for file in new_files:
                project_file = ProjectFile.objects.filter(project=project_to_save, file=file.get('name')).first()
                if not project_file:
                    try:
                        file_url = file.get('file_url')
                        info = urllib.parse.urlparse(file_url)
                        domain = info.netloc
                        # if domain and len(domain) > 0:
                        #    new_file_name = 'files/' + str(uuid.uuid4()) + '.doc'
                        #    gdown.download(file_url, new_file_name , quiet=False)
                        #    file_url = new_file_name

                        project_file = ProjectFile(project=project_to_save,
                                                   file=file.get('name'),
                                                   file_url=file_url
                                                   )
                        project_file.save()
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        logger.error("project file save error")
                        return HttpResponse(status=500)

                not_in_delete.append(project_file.id)

            ProjectFile.objects.filter(project=project_to_save).exclude(id__in=not_in_delete).delete()

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
                channels_data.append(channel.id)

            files_list = ProjectFile.objects.filter(project_id=project.id)

            files_data = []
            for file in files_list:
                files_data.append({
                    'name': file.file,
                    'id': file.id,
                })

            project_data = {
                'name': project.title,
                'work_option': project.work_option,
                'gpt_version': project.gpt_version,
                'limitForOneChat': project.per_conversation_limit,
                'limitForDay': project.outgoing_limit,
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


def file_upload(request):
    if request.method == "POST" and request.FILES.get("file"):
        try:
            # upload = request.FILES['upload']
            upload = request.FILES.get("file")
            fss = FileSystemStorage(location='files/')
            file = fss.save(upload.name, upload)
            file_url = fss.path(file)

            return JsonResponse({
                'file': file,
                'file_url': file_url
            }, safe=False)
        except Exception as e:
            logger.error(traceback.format_exc())
            return HttpResponse(status=500)
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
                recipient_to_save = Recipient.objects.filter(id=recipient_id, client=user).first()

            if not recipient_to_save:
                return HttpResponse(status=404)

            recipient_to_save.title = data.get('name')
            recipient_to_save.project_id = data.get('project')
            remote_ids = []
            remote_ids_string = data.get('mailingData')
            if remote_ids_string and len(remote_ids_string) > 0:
                for remote_id in remote_ids_string.replace('\r\n', ',').replace('\n', ',').split(','):
                    if len(remote_id) > 0:
                        remote_ids.append(remote_id)
            delimiter = '\n'
            recipient_to_save.remote_ids = delimiter.join(remote_ids)
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

            created_chats_count = Chat.objects.filter(project_id=recipient.project_id,
                                                      recipient_id=recipient.id).count()  # TODO сделать каунт тока для чатов с первысм сообщение от бота

            if recipient:

                remote_ids_len = 0
                if recipient.remote_ids and len(recipient.remote_ids) > 0:
                    remote_ids_len = len(recipient.remote_ids.replace(' ', ',').replace('\r\n', ',').replace('\n', ',').split(','))

                if created_chats_count > 0 and recipient.status == 'new':
                    recipient.status = 'active'
                recipient.save()

                if remote_ids_len <= created_chats_count and recipient.status == 'active':
                    recipient.status = 'completed'
                    recipient.save()

                recipient_data = {
                    'name': recipient.title,
                    'project': recipient.project_id,
                    'mailingData': recipient.remote_ids,
                    'date': recipient.start_date,
                    'status': recipient.status,
                    'isDate': recipient.start_date is not None,
                }

                return JsonResponse(recipient_data, safe=False)
            else:
                return HttpResponse(status=404)


def recipient_delete(request, recipient_id):
    user = request.user
    recipient_to_delete = Recipient.objects.filter(id=recipient_id, client=user).first()
    if not recipient_to_delete:
        return HttpResponse(status=404)
    else:
        recipient_to_delete.delete()
        return HttpResponse(status=200)


def recipients(request):
    recipient_list = Recipient.objects.filter(client=request.user)

    data = []
    for recipient in recipient_list:
        # Аннотация для подсчета количества контактов, активных переписок, отправленных и оставшихся сообщений

        project = Project.objects.filter(id=recipient.project_id).first()
        project_title = ''
        project_id = ''
        if project:
            project_title = project.title
            project_id = project.id
        created_chats_count = Chat.objects.filter(project_id=recipient.project_id,
                                                  recipient_id=recipient.id).count() 

        remote_ids_len = 0
        if recipient.remote_ids and len(recipient.remote_ids) > 0:
            remote_ids_len = len(recipient.remote_ids.replace(' ', ',').replace('\r\n', ',').replace('\n', ',').split(','))

        data.append({
            'title': recipient.title,
            'work_option': recipient.work_option,
            'id': recipient.id,
            'project': project_title,
            'project_id': project_id,
            'chats': remote_ids_len,
            'sent_messages': created_chats_count,
            'start_date': recipient.start_date,
            'remaining_messages': remote_ids_len - created_chats_count,
            'status': recipient.status
        })

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
                    client=user
                )
            else:
                channel_to_save = Channel.objects.filter(id=channel_id, client=user).first()

            if not channel_to_save:
                return HttpResponse(status=404)

            phone_number = re.sub(r'[^\d+]', '', data.get('phone').strip())
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number

            channel_to_save.title = data.get('phone')
            channel_to_save.source = data.get('source')
            channel_to_save.phone = phone_number

            channel_to_save.save()
            return JsonResponse({'success': True, 'created': True}, safe=False)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error("channel save error")
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
    channel_to_delete = Channel.objects.filter(id=channel_id, client=user).first()
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
        project_id = ''
        if project:
            project_title = project.title
            project_id = project.id

        data.append({
            'title': channel.title,
            'status': channel.status,
            'phone': channel.phone,
            'id': channel.id,
            'source': channel.source,
            'client_id': channel.client_id,
            'client_phone': channel.client.phone,
            'project_title': project_title,
            'project_id': project_id,
            'user': {
                'name': channel.remote_entity.get('first_name'),
                'surname': channel.remote_entity.get('last_name'),
                'avatar': None,
                'description': None,
                'username':  channel.user_id,
            },
        })

    return JsonResponse(data, safe=False)


@csrf_exempt
def telethon_sessions(request):
    response = requests.get(
        f"{TELETHON_HOST}/get-sessions",
    )
    return JsonResponse(response)


@csrf_exempt
def delete_telethon_session(request):
    response = requests.get(
        f"{TELETHON_HOST}/get-sessions",
    )

    return JsonResponse({'success': True})


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


def get_balance(request):
    client_settings = ClientSettings.objects.filter(client=request.user).first()

    current_balance = 0
    if client_settings:
        current_balance = client_settings.balance

    return JsonResponse({"balance": current_balance}, status=200)



# Шаг 2: Подтверждаем код авторизации
@csrf_exempt
def verify_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone')
            code = data.get('code')

            if not phone_number or not code:
                return JsonResponse({"message": "Номер телефона или код не предоставлены", "success": False})

            # Отправка запроса в FastAPI
            print({"phone": phone_number, "code": code})
            response = requests.post(
                f"{TELETHON_HOST}/verify-code/",
                json={"phone": phone_number, "code": code},
            )
            answer = json.loads(response.content)
            print(answer)
            if response.status_code == 200:
                # Если успех, обновляем статус в базе данных
                if answer.get('success') == True:
                    account = answer.get('account')
                    if account:
                        account = json.loads(account)
                    channel, created = Channel.objects.get_or_create(phone=phone_number, client=request.user)
                    channel.status = 'authorized'
                    channel.remote_id = account.get('id')
                    channel.remote_entity = account
                    #channel.remote_status =
                    channel.save()

                    return JsonResponse(response.json())
                if not answer.get('success'):
                    if answer.get('require_password'):
                        return JsonResponse({"message": answer.get('message'),
                                             "success": False,
                                             "require_password": True},
                                            status=response.status_code)
            else:
                return JsonResponse({"message": response.text, "success": False})
        except Exception as e:
            logger.error(traceback.format_exc())
            return JsonResponse({"message": str(e), "success": False})

    return JsonResponse({"message": "Метод запроса должен быть POST", "success": False})


def send_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone')
            password = data.get('password')

            if not phone_number or not password:
                return JsonResponse({"message": "Номер телефона или код не предоставлены", "success": False})

            # Отправка запроса в FastAPI
            print({"phone": phone_number, "password": password})
            response = requests.post(
                f"{TELETHON_HOST}/input-password/",
                json={"phone": phone_number, "password": password},
            )
            answer = json.loads(response.content)
            if response.status_code == 200:
                account = json.loads(answer.get('account'))
                # Если успех, обновляем статус в базе данных
                channel, created = Channel.objects.get_or_create(phone=phone_number, client=request.user)
                channel.status = 'authorized'
                channel.remote_id = account.get('id')
                channel.remote_entity = account
                channel.save()

                return JsonResponse({"message": "Авторизация завершена ", "success": True})
            else:
                return JsonResponse({"message": response.text, "success": False})
        except Exception as e:
            logger.error(traceback.format_exc())
            return JsonResponse({"message": str(e), "success": False})

    return JsonResponse({"message": "Метод запроса должен быть POST", "success": False})
