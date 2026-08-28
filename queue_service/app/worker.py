import pika
import os
import json
import time
from app.logging_config import setup_logging, logger
from app.service.assign_group_engine import allocate_user_to_groups
from app.auth_service_db import get_db_global

# Setup logging for the worker
setup_logging()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://user:password@192.168.0.100:5672/")
QUEUE_NAME = "post_profile_submission"
authdb = next(get_db_global())

def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        task_name = message.get("task", "unknown")
        data = message.get("raw_data", {})
        user_id = message.get("user_id", "")
        
        logger.info(f"Worker received task: {task_name}")
        logger.info(f"Processing data: {data}")
        
        # Simulate processing time
        # time.sleep(2)
        matched_groups = allocate_user_to_groups(authdb,user_id,data)
        
        logger.info(f"Successfully finished processing task: {task_name}")
        
        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # In case of error, we can either reject or re-queue
        # For simplicity, we'll re-queue once if it fails
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_worker():
    logger.info("Worker starting up and waiting for tasks...")
    
    while True:
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            
            # Ensure the queue exists
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            
            # Set prefetch count to 1 to evenly distribute tasks
            channel.basic_qos(prefetch_count=1)
            
            # Tell RabbitMQ to use our callback function
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            
            logger.info(f"Connected to RabbitMQ queue '{QUEUE_NAME}'. Waiting for messages...")
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"Connection to RabbitMQ failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
            continue
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            time.sleep(5)
            continue

if __name__ == "__main__":
    start_worker()