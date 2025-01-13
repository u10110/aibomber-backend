import json
import sys
import os
import threading
from kafka import KafkaConsumer
from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv
from apps.telegram.prsr import save_message, get_users

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


class NewChatMessageListener(threading.Thread):
    class Consumer(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.consumer = KafkaConsumer(
               bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
               auto_offset_reset='earliest',
               consumer_timeout_ms=1000)

        def run(self):
            try:
                self.consumer.consumer.subscribe(['new-chat-message'])
                while running:
                    for message in self.consumer:
                        #  message = json.loads(msg.value().decode('utf-8'))
                        channel = Channel.objects.get(phone=message.channel_phone)

                        users_response = get_users(message.channel_phone)
                        if not users_response.get("users"):
                            print(f"Нет пользователей для телефона {message.channel_phone}")
                            return
                        user_view_name = ''
                        # Шаг 3.2: Получаем сообщения для каждого пользователя
                        for user in users_response["users"]:
                            if user["id"] == message.user_id:
                                user_view_name = user["name"]

                        save_message(message, message.user_id, channel, user_view_name)
                        if self.stop_event.is_set():
                            break
            finally:
                # Close down consumer to commit final offsets.
                self.consumer.close()


class Command(BaseCommand):
    help = 'Launches Listener for new-chat-message message : Kafka'
    def handle(self, *args, **options):
        td = NewChatMessageListener()
        td.start()
        self.stdout.write("Started Consumer Thread")