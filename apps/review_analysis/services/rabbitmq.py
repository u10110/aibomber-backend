import sys
import os
import logging
import json
import ast
from loguru import logger
from decouple import config
import pika

class RabbitMqServerConfigure():
    def __init__(self):
        """Server initialization"""

        self.queue = "wb_scrapper_review_qd"
        self.host = config("RABBIT_HOST")
        self.port = config("RABBIT_PORT")
        self.routing_key = "wb_scrapper_review_qd"
        self.exchange = "mplab_scrapper_review_ed"
        self.user = config("RABBIT_USER")
        self.password = config("RABBIT_PASSWORD")


class RabbitmqServer:
    def __init__(self, server):
        """
        :param server: Object of class RabbitMqServerConfigure
        """

        self.server = server

        # url = f"amqps://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_broker_id}.mq.{region}.amazonaws.com:5671"
        # parameters = pika.URLParameters(url)

        self._credentials = pika.PlainCredentials(
            self.server.user, self.server.password
        )
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.server.host,
                port=self.server.port,
                virtual_host="/",
                credentials=self._credentials,
                heartbeat=0,
                ssl_options=None,
                # stack_timeout=10,
                blocked_connection_timeout=0,
            )
        )

        self._channel = self._connection.channel()
        self._channel.basic_qos(prefetch_count=2, global_qos=True)
        self._tem = self._channel.queue_declare(queue=self.server.queue, durable=True)
        logger.info("Server started waiting for Messages")

    def start_server(self):
        self._channel.basic_consume(
            queue=self.server.queue,
            on_message_callback=RabbitmqServer.callback,
            auto_ack=False,
        )
        logger.info("server listener started")
        self._channel.start_consuming()

    def publish(self, routing_key, message):
        # message = json.dumps(message)
        logger.info(f"[rabbit][{routing_key}] send {message}")
        method, properties, body = self._channel.basic_get(queue=routing_key)
        self._channel.basic_publish(
            exchange=self.server.exchange,
            routing_key=routing_key,
            body=str(message),
            properties=pika.BasicProperties(delivery_mode=2),
        )

    def check_messages_queue(self, routing_key, message):
        cnt = self._channel.queue_declare(
            queue=routing_key, passive=True
        ).method.message_count
        if cnt:
            for count_massages in range(cnt):
                method, properties, body = self._channel.basic_get(queue=routing_key)
                if str(message) == str(body.decode("utf-8")):
                    return False
        return True
