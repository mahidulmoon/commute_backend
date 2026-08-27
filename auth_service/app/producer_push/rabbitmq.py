import pika
import os
import json
from app.logger import logger

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://user:password@192.168.0.100:5672/")
QUEUE_NAME = "post_profile_submission"

class RabbitMQProducer:
    def __init__(self):
        self.url = RABBITMQ_URL
        self.connection = None
        self.channel = None

    def connect(self):
        try:
            params = pika.URLParameters(self.url)
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=QUEUE_NAME, durable=True)
            logger.info("Successfully connected to RabbitMQ.")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def publish_message(self, message: dict):
        if not self.channel or self.channel.is_closed:
            self.connect()
        
        try:
            body = json.dumps(message)
            self.channel.basic_publish(
                exchange="",
                routing_key=QUEUE_NAME,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                )
            )
            logger.info(f"Published message to queue '{QUEUE_NAME}': {body}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Closed RabbitMQ connection.")

# Instance to be used in the API
producer = RabbitMQProducer()