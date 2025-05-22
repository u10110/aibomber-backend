import json
import sys
import os
import time
import threading
import traceback
import datetime
from confluent_kafka import Consumer
from confluent_kafka import Producer
from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv
from apps.telegram.prsr import save_messages, get_users, get_messages
from apps.telegram.sndr import ProjectProcessor, MessageProcessor
from loguru import logger
from dateutil.parser import parse
from apps.home.models import (
    Project,
    Channel,
    Chat,
    ChatMessages
)

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
KAFKA_MESSAGES_TOPIC = os.getenv("KAFKA_MESSAGES_TOPIC", 'new-message-events')


class Command(BaseCommand):
    help = 'Launches Listener for new-chat-message message : Kafka'

    def handle(self, *args, **options):

        try:
            active_projects = Project.objects.filter(is_active=True, id=1)
            message_processor = MessageProcessor()
            for project in active_projects:
                last_message_time_lte = datetime.date.today() + datetime.timedelta(minutes=20)
                chats = Chat.objects.filter(project=project)
                logger.debug(chats.count())
                for chat in chats:
                    if chat:
                        if chat.is_auto_active \
                                and project.per_conversation_limit > message_processor.chat_messages_count(chat):

                            channel = Channel.objects.filter(id=chat.channel_id,
                                                             status='authorized').first()
                            last_message = ChatMessages.objects.filter(chat_id=chat).order_by('-created_at').first()
                            logger.debug( chat)
                            print(last_message.remote_id,channel)
                            if last_message and channel:
                                if not chat.user_id.startswith('@'):
                                    chat.user_id = "@" + chat.user_id
                                messages_response = get_messages(channel.phone, chat.user_id,
                                                                 last_message.remote_id or 0,
                                                                 last_message.created_at + datetime.timedelta(days=1))
                                logger.info(messages_response)
                                messages = messages_response.get("messages", [])  # Ожидаем массив сообщений

                                if len(messages) == 0:
                                    continue

                                last_remote_message = messages[0]

                                if last_remote_message and int(last_message.remote_id) < int(last_remote_message.get('id')):
                                    if not last_remote_message.get('to_id') \
                                            and last_remote_message.get('username') \
                                            and last_remote_message.get('text') != last_message.user_message \
                                            and last_message.message_type == 'outcoming':
                                        logger.info(f"Отправка последнего пропушенного  в кафку, чат {chat.user_id} ")
                                        payload = {
                                            "id": last_remote_message.get('id'),
                                            "date": parse(last_remote_message.get('date')).isoformat(),
                                            "username": chat.user_id,
                                            # "channel": event.message.peer_id,
                                            "via_bot_id": last_remote_message.get('via_bot_id'),
                                            "text": last_remote_message.get('text'),
                                            "sender_id": last_remote_message.get('from_id').get('user_id'),
                                            "from_id": {"user_id": last_remote_message.get('from_id').get('user_id')},
                                            "user_id": last_remote_message.get('from_id').get('user_id'),
                                            "channel_phone": channel.phone.replace('+','')
                                        }
                                        producer.produce(KAFKA_MESSAGES_TOPIC, value=json.dumps(payload))
                                        producer.flush()






        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

        logger.info('Launches Listener for new-chat-message message : Kafka')
