import json
import datetime

from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv
from loguru import logger
from apps.home.models import (
    Channel,
)
from decouple import config
import requests
import traceback

load_dotenv()


TELETHON_HOST = config("TELETHON_HOST")


class Command(BaseCommand):
    help = 'Launches Listener for new-chat-message message : Kafka'

    def handle(self, *args, **options):

        try:
            auth_channels = Channel.objects.filter(status='authorized')
            try:
                response = requests.get(f"{TELETHON_HOST}/get-sessions/")
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(e)

            res_body = json.loads(response.content)
            sessions = res_body.get('sessions', [])
            logger.debug(res_body)
            for channel in auth_channels:
                channel_session = None
                for session in sessions:
                    if session.get('phone') == channel.phone.replace('+', ''):
                        if not channel_session:
                            channel_session = session
                        else:
                            logger.info(f"channel {channel.phone} has two sessions")

                if channel_session:
                    channel.remote_id = channel_session.get('id')
                    channel.remote_entity = channel_session
                    logger.info(f"channel {channel.phone} updates")
                    channel.save()
                else:
                    channel.status = 'unauthorized'
                    logger.info(f"channel {channel.phone} unauth")
                    channel.save()

            for session in sessions:
                session_channel = None
                for channel in auth_channels:
                    if session.get('phone') == channel.phone.replace('+', ''):
                        if not session_channel:
                            session_channel = channel

                if not session_channel:
                    requests.get(f"{TELETHON_HOST}/log-out/", params={"phone": session.get('phone')})
                    logger.info(f"session {session.get('phone')}  logout")
                else:
                    if not session.get('id'):
                        logger.info(f"session {session.get('phone')} logout and channel unauth")
                        requests.get(f"{TELETHON_HOST}/log-out/", params={"phone": session.get('phone')})
                        session_channel.status = 'unauthorized'
                        session_channel.save()

        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)

        logger.info('Launches  sync telegram sessions')
