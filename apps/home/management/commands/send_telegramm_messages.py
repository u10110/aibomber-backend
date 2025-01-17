from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv
from loguru import logger
from apps.telegram.sndr import new_chat_messages
from apps.home.models import (
    Project
)


class Command(BaseCommand):
    help = 'Launches send messages to new telegram  recipients'

    def handle(self, *args, **options):
        new_chat_messages()
        logger.info('Launches  new_chat_messages')
