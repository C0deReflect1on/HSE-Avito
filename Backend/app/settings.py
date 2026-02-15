import os
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
MODERATION_TOPIC = os.getenv("MODERATION_TOPIC", "moderation")
DLQ_TOPIC = os.getenv("DLQ_TOPIC", "dlq")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "moderation_consumer_group")
API_PORT = int(os.getenv("API_PORT", "8000"))

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")