import json
import sys
import os
import time
import threading
from confluent_kafka import Consumer
from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv
from apps.telegram.prsr import save_messages, get_users
from apps.telegram.sndr import ProjectProcessor
from loguru import logger
from apps.home.models import (
    Project,
    Channel,
    Chat,
    ChatMessages
)

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")

#We want to run thread in an infinite loop
running=True


class Command(BaseCommand):
    help = 'Launches Listener for new-chat-message message : Kafka'

    def handle(self, *args, **options):
        td = NewChatMessageListener()
        td.start()
        logger.info('Launches Listener for new-chat-message message : Kafka')


class NewChatMessageListener(threading.Thread):
    class Consumer(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.consumer = Consumer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
            logger.info('new message consumer new-message-events')

        def run(self):
            try:
                while True:
                    msg = self.consumer(1.0)  # Wait for 1 second
                    if msg is None:
                        continue
                    if msg.error():
                        print("Consumer error: {}".format(msg.error()))
                        continue

                    data = json.loads(msg.value().decode('utf-8'))

                    logger.info('new message from new-message-events')
                    message = json.loads(msg.value().decode('utf-8'))
                    channel = Channel.objects.get(phone=message.channel_phone)

                    users_response = get_users(message.channel_phone)
                    if not users_response.get("users"):
                        logger.info(f"Нет пользователей для телефона {message.channel_phone}")
                        return
                    user_view_name = ''
                    # Шаг 3.2: Получаем сообщения для каждого пользователя
                    for user in users_response["users"]:
                        if user["id"] == message.user_id:
                            user_view_name = user["name"]

                    chat = save_messages(message, message.user_id, channel, user_view_name)
                    time.sleep(10)
                    ProjectProcessor.process_chat(chat, message)

                    print(f"Received message: {data}")
            finally:
                self.consumer.close()
