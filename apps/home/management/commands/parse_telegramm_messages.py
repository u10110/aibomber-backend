from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv
from loguru import logger
from apps.telegram.prsr import process_project
from apps.home.models import (
    Project
)


class Command(BaseCommand):
    help = 'Launches tg message parser'

    def handle(self, *args, **options):
        active_projects = Project.objects.filter(is_active=True)
        for project in active_projects:
            process_project(project)
        logger.info('Launches prsr')
