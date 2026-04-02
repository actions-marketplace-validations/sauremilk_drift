"""BEM target: 8 handlers all catching broad Exception."""

import logging

logger = logging.getLogger(__name__)


def connect_postgres(config):
    """Connect to PostgreSQL."""
    try:
        return {"connection": "pg", "host": config["host"]}
    except Exception:
        logger.error("PostgreSQL connection failed")
        return None


def connect_redis(config):
    """Connect to Redis."""
    try:
        return {"connection": "redis", "host": config["host"]}
    except Exception:
        logger.error("Redis connection failed")
        return None


def connect_mongodb(config):
    """Connect to MongoDB."""
    try:
        return {"connection": "mongo", "host": config["host"]}
    except Exception:
        logger.error("MongoDB connection failed")
        return None


def connect_elasticsearch(config):
    """Connect to Elasticsearch."""
    try:
        return {"connection": "es", "host": config["host"]}
    except Exception:
        logger.error("Elasticsearch connection failed")
        return None


def connect_rabbitmq(config):
    """Connect to RabbitMQ."""
    try:
        return {"connection": "rmq", "host": config["host"]}
    except Exception:
        logger.error("RabbitMQ connection failed")
        return None


def connect_kafka(config):
    """Connect to Kafka."""
    try:
        return {"connection": "kafka", "host": config["host"]}
    except Exception:
        logger.error("Kafka connection failed")
        return None


def connect_memcached(config):
    """Connect to Memcached."""
    try:
        return {"connection": "mc", "host": config["host"]}
    except Exception:
        logger.error("Memcached connection failed")
        return None


def connect_dynamodb(config):
    """Connect to DynamoDB."""
    try:
        return {"connection": "ddb", "region": config["region"]}
    except Exception:
        logger.error("DynamoDB connection failed")
        return None
