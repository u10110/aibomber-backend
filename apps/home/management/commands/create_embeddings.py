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

from apps.home.services.gpt_assistant import GPTAssistant
from apps.home.services.gpt_assistant import create_message_embedding
from apps.home.services.gpt_assistant import just_ask_question

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
KAFKA_MESSAGES_TOPIC = os.getenv("KAFKA_MESSAGES_TOPIC", 'new-message-events')


class Command(BaseCommand):
    help = 'Create or recreate embeddings for all chats and mesws'

    def handle(self, *args, **options):

        try:
            active_projects = Project.objects.filter(is_active=True, id=1)
            for project in active_projects:
                chats = Chat.objects.filter(project=project)

                logger.debug(chats.count())
                for chat in chats:
                    if chat:
                       # if chat.photo:
                       #     recipient_char = just_ask_question("Опиши человека на фото, если он там есть.", chat.photo)
                       #     print(recipient_char)
                       #     chat.recipient_char_embedding = create_message_embedding(recipient_char)
                       #     chat.save()

                        messages = ChatMessages.objects.filter(chat_id=chat).order_by('created_at')
                        for message in messages:
                            embedding = create_message_embedding(message.user_message)
                            message.message_embedding = embedding
                            message.save()



        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

        logger.info('Launches Listener for new-chat-message message : Kafka')
