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
from django.db.models.aggregates import Min
from django.utils import timezone


from apps.home.services.gpt_assistant import GPTAssistant

# Import models after Django configuration
from .models import (
    ClientSettings,
)

# Import models after Django configuration
from apps.home.models import (
    Project,
    Channel,
    Chat,
    ChatMessages
)
from decouple import config
# Constants
PID_FILE = "sndr.lock"
TELETHON_HOST = config("TELETHON_HOST")


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
            channel_phone: str,
            user_id: str
    ) -> Optional[str]:

        # Получение объекта проекта
        project = get_object_or_404(Project, id=project_id)
        logger.info(project)

        # Создание экземпляра GPTAssistant
        assistant = GPTAssistant(project=project, chat_id=chat_id, channel_phone=channel_phone, user_id=user_id)

        # Получение ответа от GPT
        try:
            answer = assistant.ask_question(question)
            return answer
        except Exception as e:

            logger.error(f"GPT Assistant connection error: {e}")
            return None

    @staticmethod
    def send_message_to_telegram(phone: str, user_id: str, message: str) -> bool:
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
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return False


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
            remaining_messages__gt=0,
            is_active=True
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

        today_send_new_messages = ChatMessages.objects.filter(
            chat_id__in=Chat.objects.filter(channel=channel),
            created_at__gte=(datetime.datetime.now(tz=timezone.utc) - datetime.timedelta(days=1))
        ).values('chat_id_id').annotate(min_created_at=Min('created_at')).count()

        if today_send_new_messages>=channel.max_daily_messages:
            logger.info(f"У канала: {channel.id}, телефон: {channel.phone} достигнут дневной лимит новых сообщений")


        try:
            # Получаем TG ID, у которых нет сообщений
            chat_for_current_channel_message = Chat.objects.filter(
                project=project,  # Связь через таблицу Recipient
                is_auto_active=True,
                last_message_time=None
            ).first()

            # Обрабатываем существующий
            if not chat_for_current_channel_message:
                logger.info(f"Нет новых активных чатов для телефона {channel.phone}")
                return

            # Обрабатываем новых пользователей

            logger.info(f"Новый получатель {chat_for_current_channel_message.user_id}")
            message = message_processor.send_to_gpt_assistant(
                chat_id=chat_for_current_channel_message.id,
                project_id=project.id,
                question="",  # Пустой вопрос для нового пользователя
                channel_phone=channel.phone,
                user_id=chat_for_current_channel_message.user_id
            )
            logger.info(message)
            if message:
                sent = message_processor.send_message_to_telegram(
                    channel.phone,
                    chat_for_current_channel_message.user_id,
                    message)
                logger.info(sent)
                if sent:
                    ChatMessages.objects.create(
                        chat_id=chat_for_current_channel_message,
                        user_name=channel.phone,
                        user_message=message[:555],
                        message_type="outcoming"
                    )
                    channel.remaining_messages = F('remaining_messages') - 1
                    channel.save()
                else:
                    chat = Chat.objects.filter(
                        id=chat_for_current_channel_message.id
                    ).first()
                    chat.status = 'error'
                    chat.last_message_time = datetime.datetime.now(tz=timezone.utc)
                    chat.save()
                    logger.info(f"Ошибка отправки сообщения {chat_for_current_channel_message.user_id} ")
            else:
                logger.info(f"Ошибка при генерации сообщения {chat_for_current_channel_message.user_id} ")
        except Exception as e:
            logger.info(f"Ошибка при обработке канала {channel.title}: ")

    @staticmethod
    def process_chat(
            chat: Chat,
            message_processor: MessageProcessor
    ) -> None:

        combined_message = message_processor.get_combined_messages(chat)
        logger.debug(combined_message)
        if not combined_message:
            return

        message = message_processor.send_to_gpt_assistant(
            chat_id=chat.id,
            project_id=chat.channel.project_id,
            question=combined_message,
            channel_phone=chat.channel,
            user_id=chat.user_id
        )

        if message:
            if message_processor.send_message_to_telegram(
                   chat.channel.phone,
                   chat.user_id,
                   message
            ):
                ChatMessages.objects.create(
                    chat_id=chat,
                    user_name=chat.channel.phone,
                    user_message=message[:555],
                    message_type="outcoming"
                )
            chat.channel.remaining_messages = F('remaining_messages') - 1
            chat.channel.save()


def new_chat_messages():
    """Главная функция выполнения задачи."""
    # if not ProcessLockManager.check_and_create_lock():
    #     sys.exit(1)

    try:
        current_time = datetime.datetime.now().time()
        clients = ClientManager.get_active_clients()

        for client in clients:
            logger.info(f"Обработка клиента {client.client_id}")
            if client.balance >0:
                logger.info(f"Баланс клиента {client.balance}")
                projects = ClientManager.get_active_projects(client, current_time)
                if projects.count() == 0:
                    logger.info(f"клиент {client.client_id} не имеет проектов для выполнения на данный момент")
                project_processor = ProjectProcessor()
                for project in projects:
                    project_processor.process_project(project)
            else:
                logger.info(f"Нулевой баланс у клиента {client.balance}")

    finally:
        ProcessLockManager.remove_lock()

