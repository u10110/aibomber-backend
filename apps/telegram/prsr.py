
import os
import datetime
import requests
from django.db.models import F
from decouple import config
from apps.home.services.gpt_assistant import GPTAssistant
# Import models after Django configuration
from loguru import logger
from apps.home.models import (
    Project,
    Channel,
    Chat,
    ChatMessages
)

# Import models after Django configuration
from .models import (
    ClientSettings,
)
import sys
# Загружаем переменные окружения из файла .env


TELETHON_HOST = config("TELETHON_HOST")


def get_active_clients():
    """
    Получает всех клиентов с положительным балансом.
    """
    return ClientSettings.objects.filter(balance__gt=0)


def get_active_projects(client, current_time):
    """
    Получает проекты клиента, активные в данный момент времени.
    """
    return Project.objects.filter(
        client=client.client_id,
        is_active=True,
        time_start__lte=current_time,
        time_end__gte=current_time,
    )


def process_channel(channel , project):
    """
    Обрабатывает один канал:
    - Получает пользователей через get-users
    - Для каждого пользователя получает сообщения через get-messages
    - Сохраняет новые сообщения в базу
    """
    try:
        print(f"Получение пользователей для канала {channel.phone}")
        phone = channel.phone  # Используем телефон, привязанный к каналу

        # Шаг 3.1: Получаем пользователей для данного номера телефона
        users_response = get_users(phone)
        if not users_response.get("users"):
            print(f"Нет пользователей для телефона {phone}")
            return

        # Шаг 3.2: Получаем сообщения для каждого пользователя
        for user in users_response["users"]:
            user_id = user["id"]
            user_view_name = user["name"]
            print(user)
            print(f"Получение сообщений для пользователя {user_id}")

            last_message = ChatMessages.objects.filter(
                chat_id__in=Chat.objects.filter(user_id=user_id, channel=channel),
            ).order_by('-created_at').first()
            offset_date = datetime.datetime.now() - datetime.timedelta(days=1)
            if last_message is not None:
                offset_date = last_message.created_at

            messages_response = get_messages(phone, user_id, offset_date)
            messages = messages_response.get("messages", [])  # Ожидаем массив сообщений

            if messages:
                print(f"Сохранение сообщений для пользователя {user_id}")
                save_messages(user_id, messages, project, channel, user_view_name)
            else:
                print(f"Нет новых сообщений для пользователя {user_id}")

        # Уменьшаем оставшиеся сообщения в канале

        channel.save()
    except Exception as e:
        print(e.format_exc())
        print(f"Ошибка обработки канала {channel.title}: {e}")


def save_messages(user_id, messages, project, channel, user_view_name):
    """
    Сохраняет каждое сообщение из списка в базу данных, проверяя уникальность.
    """

    _USER_NAME = next((message.get("username") for message in messages if message.get("username")), None)
    chat = None

    for message in messages:
        message_text = message.get("text", "")
        message_id = message.get("id", None)  # ID сообщения
        sender_id = message.get("sender_id", None)  # ID отправителя
        message_date = message.get("date", None)  # Дата сообщения от Telethon
        user_name = message.get('username', None)
        from_id = message.get("from_id", None)
        to_id = message.get("to_id", None)

        if not message_text or not message_id or not sender_id or not message_date or sender_id == 777000:
            continue  # Пропускаем сообщения с отсутствующими полями
        # Определяем, кто отправил сообщение: GPT Assistant или другой пользователь
        logger.info(f"Сообщение получено {user_name}: {message_id}")
        if user_name:

            chat = Chat.objects.filter(
                project=project,
                channel=channel,
                remote_chat_id=from_id
            ).order_by('-last_message_time').first()
            if not chat:
                chat = Chat(
                    project=project,
                    user_id=_USER_NAME,
                    channel=channel,
                    user_name=user_view_name,
                    remote_chat_id=from_id
                )
                chat.save()



            # Проверяем, существует ли сообщение в базе
            existing_message = ChatMessages.objects.filter(
                chat_id=chat,
                remote_id=message_id  # Проверка по ID сообщения
            ).exists()

            if not existing_message:

                # Создаём новое сообщение в базе
                ChatMessages.objects.create(
                    chat_id=chat,
                    message_type="incoming",
                    user_message=message_text[:555],
                    remote_id=message_id,  # Сохраняем ID сообщения
                    created_at=message_date,
                    remote_message=message
                )

                logger.info(f"Сообщение сохранено для пользователя {user_name}: {message_id}")
            else:
                logger.info(f"Сообщение уже существует для пользователя {user_id}: {message_id}")

    return chat


def process_project(project):
    """
    Обрабатывает один проект:
    - Фильтрует активные каналы
    - Получает пользователей (TG ID)
    - Отправляет запросы и сохраняет сообщения
    """
    # Шаг 4: Получаем активные каналы проекта
    channels = Channel.objects.filter(
        project_id=project.id,
        status="authorized"
    )
    if not channels.exists():
        print(f"Проект {project.id} не имеет активных каналов")
        return



    # Шаг 7: Обрабатываем каналы
    for channel in channels:
        print(f"Обработка канала {channel.title}")
        process_channel(channel, project)


def get_existing_chats(tgid_list):
    """
    Получает существующие чаты для заданных TG ID.
    """
    return {
        chat.user_id: chat  # Преобразуем ключи в числа
        for chat in Chat.objects.filter(user_id__in=tgid_list.values_list("user_id", flat=True))
    }


def get_users(phone):
    """
    Отправляет запрос для получения списка пользователей.
    """
    url = f"{TELETHON_HOST}/get-users/?phone={phone}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка получения пользователей: {response.text}")
            return {}
    except Exception as e:
        print(f"Ошибка соединения с get-users: {e}")
        return {}


def get_messages(phone, user_id, offset_id, offset_date):
    """
    Отправляет запрос для получения сообщений от пользователя.
    """
    url = f"{TELETHON_HOST}/get-messages/"
    payload = {
        "phone": phone,
        "user_id": user_id,
        "offset_date": offset_date.isoformat(),
        "offset_id": offset_id,
        'limit': 10000
    }
    print(payload)
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка получения сообщений: {response.text}")
            return {}
    except Exception as e:
        print(f"Ошибка соединения с get-messages: {e}")
        return {}


