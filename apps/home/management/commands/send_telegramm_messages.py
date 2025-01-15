from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv
from loguru import logger
from apps.telegram.sndr import ProjectProcessor
from apps.home.models import (
    Project
)


class Command(BaseCommand):
    help = 'Launches Listener for new-chat-message message : Kafka'

    def handle(self, *args, **options):
        active_projects = Project.objects.filter(is_active=True)
        for project in active_projects:
            ProjectProcessor.process_project(project)
        logger.info('Launches Listener for new-chat-message message : Kafka')
