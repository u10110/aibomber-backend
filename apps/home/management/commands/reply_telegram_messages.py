import json
import sys
import os
import time
import threading
import traceback
from confluent_kafka import Consumer
from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv
from apps.telegram.prsr import save_messages, get_users
from apps.telegram.sndr import ProjectProcessor, MessageProcessor
from loguru import logger
from apps.home.models import (
    Project,
    Channel,
    Chat,
    ChatMessages
)

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")


class Command(BaseCommand):
    help = 'Launches Listener for new-chat-message message : Kafka'

    def handle(self, *args, **options):
        consumer = Consumer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                             'group.id': 'group-1',
                             'auto.offset.reset': 'earliest'})
        try:
            consumer.subscribe(['new-message-events'])
            logger.info("subscribed  to new-message-events")
            while True:
                msg = consumer.poll(1.0)  # Wait for 1 second
                if msg is None:
                    continue
                if msg.error():
                    logger.info("Consumer error: {}".format(msg.error()))
                    continue

                message = json.loads(msg.value().decode('utf-8'))
                logger.info(f"new message from new-message-events {message.get('channel_phone')}")
                channel = Channel.objects.get(phone='+' + message.get('channel_phone'))

                users_response = get_users(message.get('channel_phone'))
                if not users_response.get("users"):
                    logger.info(f"Нет пользователей для телефона {message.get('channel_phone')}")
                    return
                user_view_name = ''
                # Шаг 3.2: Получаем сообщения для каждого пользователя
                for user in users_response["users"]:
                    if user["id"] == message.get('user_id'):
                        user_view_name = user["name"]

                project = Project.objects.filter(id=channel.project_id).get()

                logger.info(f"saving message {message.get('user_id')}")
                chat = save_messages(message.get('user_id'), [message], project, channel, user_view_name)
                if chat:
                    time.sleep(10)
                    message_processor = MessageProcessor()
                    ProjectProcessor.process_chat(chat, message_processor)
                else:
                    logger.error(f"Сообщение получено но не обработано, нехватает "
                          f"данных или недопустмый отправитель: {message.get('text', '')}")
                logger.debug(f"Received message: {chat.id}")
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
        finally:
            consumer.close()

        logger.info('Launches Listener for new-chat-message message : Kafka')

