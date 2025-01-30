import json
import sys
import os
import time
import threading
import traceback
import datetime
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


class Command(BaseCommand):
    help = 'Launches Listener for new-chat-message message : Kafka'

    def handle(self, *args, **options):

        try:
            active_projects = Project.objects.filter(is_active=True,id=69)
            for project in active_projects:
                last_message_time_lte = datetime.date.today() + datetime.timedelta(minutes=3)
                chats = Chat.objects.filter(project=project, last_message_time__lte=last_message_time_lte)
                for chat in chats:
                    if chat:
                        if chat.is_auto_active:
                            #time.sleep(10)
                            message_processor = MessageProcessor()
                            if project.per_conversation_limit > message_processor.chat_messages_count(chat):
                                ProjectProcessor.process_chat(chat, message_processor)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)


        logger.info('Launches Listener for new-chat-message message : Kafka')

