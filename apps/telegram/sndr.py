"""
Telegram Message Sender Service
This module handles automated message sending via Telegram based on client settings and projects.
"""
from loguru import logger
from typing import List, Dict, Optional
import os
import datetime
import requests
from django.db.models import F, QuerySet
from django.shortcuts import get_object_or_404
from django.db.models.aggregates import Min, Max
from django.utils import timezone
import time
import traceback
import json
from apps.home.services.gpt_assistant import GPTAssistant
from apps.home.services.gpt_assistant import create_message_embedding
from apps.home.services.gpt_assistant import just_ask_question
from django.db.models import Q
from PyPDF2 import PdfReader
from docx import Document

# Import models after Django configuration
from .models import (
    ClientSettings,
)

# Import models after Django configuration
from apps.home.models import (
    Project,
    Channel,
    Chat,
    ChatMessages,
    Recipient
)
from decouple import config

# Constants
PID_FILE = "sndr.lock"
TELETHON_HOST = config("TELETHON_HOST")

MESSAGE_SENT_STATUSES = [
    'SENT',
    'ERROR',
    'USER_DOESNT_EXIST'
]


class ProcessLockManager:
    """Manages process locking to prevent multiple instances."""

    @staticmethod
    def check_and_create_lock() -> bool:
        """
        Check if process is running and create lock file if not.
        
        Returns:
            bool: True if lock was created, False if process is already running
        """
        if os.path.exists(PID_FILE):
            logger.info("sndr.py is already running.")
            return False

        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        return True

    @staticmethod
    def remove_lock():
        """Remove the process lock file."""
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


class ClientManager:
    """Handles client-related operations."""

    @staticmethod
    def get_active_clients() -> QuerySet:
        """
        Get all clients with positive balance.
        
        Returns:
            QuerySet: Active clients with balance > 0
        """
        clients = ClientSettings.objects.all()
        return clients

    @staticmethod
    def get_active_projects(client: ClientSettings, current_time: datetime.time) -> QuerySet:
        """
        Get active projects for a client at current time.
        
        Args:
            client: Client settings object
            current_time: Current time to check project activity
            
        Returns:
            QuerySet: Active projects for the client
        """
        logger.debug(current_time)
        return Project.objects.filter(
            client=client.client_id,
            is_active=True,
            time_start__lte=current_time,
            time_end__gte=current_time,
        )


class MessageProcessor:
    """Handles message processing and sending."""

    @staticmethod
    def get_combined_messages(Chat: Chat) -> Optional[str]:
        """
        Combine new messages from chat into single text.

        Args:
            chat: Chat object to process
            
        Returns:
            Optional[str]: Combined messages or None if no new messages
        """
        last_answer = ChatMessages.objects.filter(
            chat_id=Chat,
            message_type="outcoming"
        ).order_by('-created_at').first()

        query_filter = {
            'chat_id': Chat.id,
            'message_type': "incoming"
        }

        if last_answer:
            query_filter['created_at__gt'] = last_answer.created_at

        new_messages = ChatMessages.objects.filter(**query_filter).order_by('-created_at')

        return "\n".join(new_messages.values_list("user_message", flat=True)) if new_messages.exists() else None

    @staticmethod
    def send_to_gpt_assistant(
            chat_id: int,
            project_id: int,
            question: str,
            channel: str,
            photo: str,
            user_id: str
    ) -> Optional[str]:

        # Получение объекта проекта
        project = get_object_or_404(Project, id=project_id)

        # Создание экземпляра GPTAssistant
        assistant = GPTAssistant(project=project, chat_id=chat_id, channel_phone=channel, user_id=user_id)

        # Получение ответа от GPT
        try:
            answer = assistant.ask_question(question, photo)
            chat_status = assistant.ask_chat_status()
            logger.debug(chat_status)
            if chat_status == 'interest_shown' or chat_status == 'contact_received':
                MessageProcessor.send_message_to_telegram(channel.phone, '@ai_bomber',  user_id + ' status ' + chat_status )

            return answer
        except Exception as e:

            logger.error(f"GPT Assistant connection error: {e}")
            return None

    @staticmethod
    def send_message_to_telegram(phone: str, user_id: str, message: str) -> requests:
        """Send message via Telegram API."""

        if not user_id.startswith('@'): user_id = '@' + user_id

        payload = {
            "phone": phone,
            "username": user_id,
            "message": message
        }

        try:
            response = requests.post(
                f"{TELETHON_HOST}/send-message/",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            logger.debug(f"Ответ сервера телетон:{response.status_code}")
            return response

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"Telegram API error: {e}")
            return False

    @staticmethod
    def chat_messages_count(chat):
        return ChatMessages.objects.filter(chat_id=chat, message_type='outcoming').count()


class ProjectProcessor:
    """Управляет обработкой проектов и их каналов."""

    @staticmethod
    def process_project(project: Project) -> None:
        """
        Обрабатывает отдельный проект: фильтрует активные каналы, 
        получает TG ID и обрабатывает новые сообщения.

        Args:
            project: Объект проекта для обработки
        """
        logger.info(f"Обработка Проекта  {project.id}")
        # Получаем активные каналы проекта
        channels = Channel.objects.filter(
            client=project.client_id,
            project_id=project.id,
            status='authorized'
        )

        if not channels.exists():
            logger.info(f"Проект {project.id}  {project.title} не имеет активных каналов")
            return

        # Обрабатываем каждый канал
        for channel in channels:
            ProjectProcessor._process_single_channel_for_new_message(channel, project)

    @staticmethod
    def _process_single_channel_for_new_message(channel: Channel, project: Project) -> None:
        logger.info(f"Обработка канала: {channel.id}, телефон: {channel.phone}")

        message_processor = MessageProcessor()

        today_send_new_messages = ChatMessages.objects \
            .filter(chat_id__in=(Chat.objects.filter(channel=channel, project=project)) \
                    .filter(created_at__gte=(datetime.datetime.now(tz=timezone.utc) - datetime.timedelta(days=1)))
                    ).values('chat_id_id').annotate(min_created_at=Min('created_at')).count()
        logger.debug(today_send_new_messages)
        if today_send_new_messages >= project.outgoing_limit:
            logger.info(f"У канала: {channel.id}, телефон: {channel.phone} достигнут дневной лимит новых сообщений")
            return

        try:

            new_chat_in_2400_sec = Chat.objects.filter(
                channel=channel,
                created_at__gte=(datetime.datetime.now(tz=timezone.utc) - datetime.timedelta(seconds=2400))
            ).annotate(max_created_at=Max('created_at')).count()

            new_chat_in_day_fr_channel = Chat.objects.filter(
                channel=channel,
                created_at__gte=(datetime.datetime.now(tz=timezone.utc) - datetime.timedelta(seconds=86400))
            ).annotate(max_created_at=Max('created_at')).count()

            # Получаем TG ID, у которых нет сообщений
            next_recipient = ProjectProcessor.get_next_new_recipient(project)
            logger.info(next_recipient)
            # Обрабатываем существующий\

            if new_chat_in_day_fr_channel > 4:
                logger.info(f"Для канала {channel.id}  {channel.phone} достигнут лимит новых  чатов в день")
                return
            else:
                logger.info(f"Для канала {channel.id}  {channel.phone}  осталось {new_chat_in_day_fr_channel} за сегодня")


            if new_chat_in_2400_sec > 0:
                logger.info(f"ждем 40 минут для нового сообщения {project.title}  {channel.phone}")
                return

            if not next_recipient:
                logger.info(f"Нет новых получателей  для проекта {project.title} ")
            else:
                logger.info(f"создаем и отправляем первое сообщение")
                # Обрабатываем новых пользователе

                info_response = requests.get(f"{TELETHON_HOST}/get-user-info/",
                                             params={"phone": channel.phone, "username": next_recipient.get('user_name')
                                                     })

                recipient_info = json.loads(info_response.content)

                photo_url = None
                if recipient_info.get('photo', None) is not None and recipient_info.get('photo', None) != '':
                    photo_url = f"{TELETHON_HOST}/get-user-photo?photo={recipient_info.get('photo')}"

                user_name = ''
                if  recipient_info.get('first_name') is not None:
                    user_name=recipient_info.get('first_name')

                if  recipient_info.get('last_name') is not None:
                    user_name+=recipient_info.get('last_name')

                recipient_char = just_ask_question("Опиши человека на фото, если он там есть.", photo_url)
                recipient_char_embedding = create_message_embedding(recipient_char)

                chat_for_current_channel_message = Chat(
                    project=project,
                    user_id=next_recipient.get('user_name'),
                    recipient_id=next_recipient.get('recipient_id'),
                    photo=photo_url,
                    recipient_char_embedding=recipient_char_embedding,
                    user_name=user_name,
                    channel=channel
                )
                chat_for_current_channel_message.save()

                logger.info(
                    f"Создан новый чат для {chat_for_current_channel_message.id} {next_recipient.get('user_name')}")

                message = message_processor.send_to_gpt_assistant(
                    chat_id=chat_for_current_channel_message.id,
                    project_id=project.id,
                    question="Сгенерируй приветственное сообщение для '" + user_name + "' на основе шаблона '" + project.hello_text + "'.  ",  # Пустой вопрос для нового пользователя
                    channel=channel,
                    photo=chat_for_current_channel_message.photo,
                    user_id=chat_for_current_channel_message.user_id
                )

                embedding = create_message_embedding(message)

                logger.debug(message)
                if message:
                    new_message = ChatMessages.objects.create(
                        chat_id=chat_for_current_channel_message,
                        user_message=message[:555],
                        message_type="outcoming",
                        remote_status="send",
                        message_embedding=embedding
                    )

                    created_chats_count_for_recipient = Chat.objects.filter(project_id=project.id,
                                                                            recipient_id=next_recipient.get(
                                                                                'recipient_id')).count()
                    recipient_for_update_status = Recipient.objects.filter(id=next_recipient.get('recipient_id')).first()
                    remote_ids_len = 0
                    if recipient_for_update_status.remote_ids and len(recipient_for_update_status.remote_ids) > 0:
                        remote_ids_len = len(
                            recipient_for_update_status.remote_ids.replace(' ', ',').replace('\r\n', ',').replace('\n', ',').split(','))

                    if created_chats_count_for_recipient > 0 and recipient_for_update_status.status == 'new':
                        if not recipient_for_update_status.start_date:
                            recipient_for_update_status.start_date = datetime.datetime.now(tz=timezone.utc)
                        recipient_for_update_status.status = 'active'
                        recipient_for_update_status.save()

                    if remote_ids_len <= created_chats_count_for_recipient \
                            and recipient_for_update_status.status == 'active':
                        recipient_for_update_status.status = 'completed'
                        recipient_for_update_status.save()

                    response = message_processor.send_message_to_telegram(
                        channel.phone,
                        chat_for_current_channel_message.user_id,
                        message)
                    response_body = json.loads(response.content)
                    if response.status_code == 200:
                        remote_message_entity = json.loads(response_body.get('result'))
                        logger.debug(remote_message_entity)
                        chat_for_current_channel_message.remote_chat_id = remote_message_entity.get('to_id')
                        chat_for_current_channel_message.save()

                        new_message.remote_id = remote_message_entity.get('id')
                        new_message.remote_message = remote_message_entity
                        new_message.remote_status = 'deliver'
                        new_message.save()

                    if response.status_code == 404:
                        chat_for_current_channel_message.status = response_body.get('detail')
                        chat_for_current_channel_message.last_message_time = datetime.datetime.now(tz=timezone.utc)
                        chat_for_current_channel_message.save()

                        logger.debug(response_body)
                        logger.info(f"user_doesnt_exist {chat_for_current_channel_message.user_id} ")

                        chat_for_current_channel_message.save()

                    if response.status_code == 500:
                        logger.debug(response_body)
                        logger.info(f"Ошибка отправки {chat_for_current_channel_message.user_id} ")
                        if  response_body.get('detail') == 'banned':
                            channel.status = 'banned'
                            channel.save()
                        chat_for_current_channel_message.status = response_body.get('detail')
                        chat_for_current_channel_message.save()
                        new_message.remote_status = response_body.get('detail')
                        new_message.save()

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.info(f"Ошибка при обработке канала {channel.title}: ")

    @staticmethod
    def process_chat(
            chat: Chat,
            message_processor: MessageProcessor
    ) -> None:

        combined_message = message_processor.get_combined_messages(chat)

        if not combined_message:
            return

        message = message_processor.send_to_gpt_assistant(
            chat_id=chat.id,
            project_id=chat.channel.project_id,
            question=combined_message,
            channel=chat.channel,
            photo=None,
            user_id=chat.user_id
        )
        logger.debug("GPT подготовил ответ")
        if message:
            result = message_processor.send_message_to_telegram(
                chat.channel.phone,
                chat.user_id,
                message)
            logger.debug(result)
            embedding = create_message_embedding(message)
            if result and result.status_code == 200:
                logger.info(f"message sended {message} ")
                ChatMessages.objects.create(
                    chat_id=chat,
                    user_message=message[:555],
                    message_type="outcoming",
                    embedding = embedding
                )
            chat.channel.save()

    @staticmethod
    def get_next_new_recipient(project: Project):
        recipients = Recipient.objects.filter(project_id=project.id, status__in=['new', 'active'])
        for recipient in recipients:

            if recipient.start_date and recipient.start_date >= datetime.datetime.now(tz=timezone.utc):
                logger.debug(f"Расслка  {recipient.title} отложена по дате {recipient.start_date}")
                continue

            for remote_id in recipient.remote_ids.replace(' ', ',').replace('\r\n', ',').replace('\n', ',').split(','):
                if len(remote_id) > 0:
                    chat = Chat.objects.filter(project=project,
                                               recipient_id=recipient.id,
                                               user_id__endswith=remote_id).first()
                    if not chat:
                        user_name = remote_id
                        if not remote_id.startswith('@'):
                            user_name = "@" + remote_id

                        logger.debug(f"Новый получаетль {user_name} проект {project.id}")
                        return {
                            'user_name': user_name,
                            'recipient_id': recipient.id
                        }
                    # else:
                    #    logger.debug(f"Чат найден для {remote_id}")
        return None


def new_chat_messages(project_id=None):
    """Главная функция выполнения задачи."""
    # if not ProcessLockManager.check_and_create_lock():
    #     sys.exit(1)

    try:
        current_time = datetime.datetime.now().time()
        clients = ClientManager.get_active_clients()
        logger.info(current_time)
        logger.debug(clients)
        for client in clients:
            logger.info(f"Обработка клиента {client.client_id}")
            if client.balance > 0:
                logger.info(f"Баланс клиента {client.balance}")
                if not project_id:
                    projects = ClientManager.get_active_projects(client, current_time)
                else:
                    projects = Project.objects.filter(id=project_id)

                if projects.count() == 0:
                    logger.info(f"клиент {client.client_id} не имеет проектов для выполнения на данный момент")
                project_processor = ProjectProcessor()
                for project in projects:
                    project_processor.process_project(project)
            else:
                logger.info(f"Нулевой баланс у клиента {client.balance}")

    finally:
        ProcessLockManager.remove_lock()
