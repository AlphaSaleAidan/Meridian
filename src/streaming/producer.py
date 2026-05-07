"""
Redpanda/Kafka event producer for camera detection events.

Publishes structured detection results (person counts, zone entries/exits,
dwell times) to Kafka topics for async consumption by the persistence
and analysis layers.
"""
import json
import logging
import os
from typing import Any

logger = logging.getLogger("meridian.streaming.producer")

KAFKA_BROKERS = os.environ.get("KAFKA_BROKERS", "localhost:9092")
DETECTION_TOPIC = os.environ.get("KAFKA_DETECTION_TOPIC", "meridian.camera.detections")
INSIGHT_TOPIC = os.environ.get("KAFKA_INSIGHT_TOPIC", "meridian.insights")

_producer = None
_available = False


def _get_producer():
    global _producer, _available
    if _producer is not None:
        return _producer
    try:
        from confluent_kafka import Producer
        _producer = Producer({
            "bootstrap.servers": KAFKA_BROKERS,
            "client.id": "meridian-camera-producer",
            "acks": "all",
            "retries": 3,
            "linger.ms": 10,
        })
        _available = True
        logger.info(f"Kafka producer connected to {KAFKA_BROKERS}")
        return _producer
    except ImportError:
        logger.info("confluent-kafka not installed — event streaming disabled")
    except Exception as e:
        logger.warning(f"Kafka producer init failed: {e}")
    return None


def _delivery_callback(err, msg):
    if err:
        logger.error(f"Kafka delivery failed: {err}")
    else:
        logger.debug(f"Delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}")


def publish_detection(merchant_id: str, camera_id: str, detection: dict):
    producer = _get_producer()
    if not producer:
        return False
    event = {
        "type": "detection",
        "merchant_id": merchant_id,
        "camera_id": camera_id,
        "data": detection,
    }
    try:
        producer.produce(
            DETECTION_TOPIC,
            key=f"{merchant_id}:{camera_id}",
            value=json.dumps(event, default=str),
            callback=_delivery_callback,
        )
        producer.poll(0)
        return True
    except Exception as e:
        logger.error(f"Failed to publish detection: {e}")
        return False


def publish_insight(merchant_id: str, agent_name: str, insight: dict):
    producer = _get_producer()
    if not producer:
        return False
    event = {
        "type": "insight",
        "merchant_id": merchant_id,
        "agent": agent_name,
        "data": insight,
    }
    try:
        producer.produce(
            INSIGHT_TOPIC,
            key=f"{merchant_id}:{agent_name}",
            value=json.dumps(event, default=str),
            callback=_delivery_callback,
        )
        producer.poll(0)
        return True
    except Exception as e:
        logger.error(f"Failed to publish insight: {e}")
        return False


def flush(timeout: float = 5.0):
    if _producer:
        _producer.flush(timeout)
