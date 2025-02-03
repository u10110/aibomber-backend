from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv
from loguru import logger
from apps.telegram.sndr import new_chat_messages
from apps.home.models import (
    Project
)
import time


class Command(BaseCommand):
    help = 'Launches send messages to new telegram  recipients'

    def handle(self, *args, **options):
        while True:
            try:
                new_chat_messages(100)
                time.sleep(10)
            except Exception as e:
                logger.error(e)
        logger.info('Launches  new_chat_messages')
