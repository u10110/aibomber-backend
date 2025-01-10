
import os
import datetime
import requests
from django.db.models import F
from decouple import config
from apps.home.services.gpt_assistant import GPTAssistant
# Import models after Django configuration
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


FASTAPI_HOST = config("FASTAPI_HOST")


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

            messages_response = get_messages(phone, user_id)
            messages = messages_response.get("messages", [])  # Ожидаем массив сообщений

            if messages:
                print(f"Сохранение сообщений для пользователя {user_id}")
                save_messages(user_id, messages, project, channel, user_view_name)
            else:
                print(f"Нет новых сообщений для пользователя {user_id}")

        # Уменьшаем оставшиеся сообщения в канале
        channel.remaining_messages = F('remaining_messages') - 1
        channel.save()
    except Exception as e:
        print(e.format_exc())
        print(f"Ошибка обработки канала {channel.title}: {e}")


def save_messages(user_id, messages, project, channel, user_view_name):
    """
    Сохраняет каждое сообщение из списка в базу данных, проверяя уникальность.
    """

    _USER_NAME = next((message.get("username") for message in messages if message.get("username")), None)


    for message in messages:
        message_text = message.get("text", "")
        message_id = message.get("id", None)  # ID сообщения
        sender_id = message.get("user_id", None)  # ID отправителя
        message_date = message.get("date", None)  # Дата сообщения от Telethon
        user_name = message.get('username', None)
        from_id = message.get("from_id", None)
        to_id = message.get("to_id", None)

        if not message_text or not message_id or not sender_id or not message_date or sender_id == 777000:
            continue  # Пропускаем сообщения с отсутствующими полями
       # print(message)
        print(user_id,sender_id, user_name, to_id, from_id)
        # Определяем, кто отправил сообщение: GPT Assistant или другой пользователь
        if sender_id != user_id and user_name is None:
            user_name = "GPT Assistant"
        else:
            user_name = _USER_NAME

        if user_name:
            try:
                chat = Chat.objects.get(
                    project=project,
                    user_id=user_name,
                    channel=channel,
                )
            except Chat.DoesNotExist:
                chat = Chat(
                    project=project,
                    user_id=user_name,
                    channel=channel,
                    user_name=user_view_name
                )
                chat.save()

            # Создание экземпляра GPTAssistant
            assistant = GPTAssistant(project=project, chat_id=chat.id, channel_phone=channel.phone, user_id=user_id)
            print(f"Получение статуса общения {user_id}")
            # Получение ответа от GPT
            try:
                text_status = assistant.ask_chat_status()
                if Chat.CHAT_STATUS[text_status] is not None:
                    chat.status = text_status
                    chat.save()
            except Exception as e:
                print(f"text_status get error : {text_status}")
                return None

            # Проверяем, существует ли сообщение в базе
            existing_message = ChatMessages.objects.filter(
                messageId=message_id,  # Проверка по ID сообщения
            ).exists()

            if not existing_message:

                # Создаём новое сообщение в базе
                ChatMessages.objects.create(
                    chat_id=chat,
                    message_type="incoming" if to_id is None else "outcoming",
                    user_name=sender_id,
                    user_message=message_text,
                    messageId=message_id,  # Сохраняем ID сообщения
                    created_at=message_date,
                )

                print(f"Сообщение сохранено для пользователя {user_name}: {message_id}")
            else:
                print(f"Сообщение уже существует для пользователя {user_id}: {message_id}")


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
        status="authorized",
        remaining_messages__gt=0,
        is_active=True,
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
    url = f"{FASTAPI_HOST}/get-users/?phone={phone}"
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


def get_messages(phone, user_id):
    """
    Отправляет запрос для получения сообщений от пользователя.
    """
    url = f"{FASTAPI_HOST}/get-messages/"
    payload = {
        "phone": phone,
        "user_id": user_id,
        "limit": 50,
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


