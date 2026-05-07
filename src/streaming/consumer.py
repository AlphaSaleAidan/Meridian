"""
Redpanda/Kafka consumer for processing camera detection events.

Consumes detection events and routes them to the appropriate
handlers: persistence (Supabase), agent triggers, and metrics.
"""
import json
import logging
import os
from typing import Callable

logger = logging.getLogger("meridian.streaming.consumer")

KAFKA_BROKERS = os.environ.get("KAFKA_BROKERS", "localhost:9092")
DETECTION_TOPIC = os.environ.get("KAFKA_DETECTION_TOPIC", "meridian.camera.detections")
CONSUMER_GROUP = os.environ.get("KAFKA_CONSUMER_GROUP", "meridian-detection-workers")


class DetectionConsumer:
    """Consumes camera detection events from Kafka/Redpanda."""

    def __init__(self, handlers: list[Callable] | None = None):
        self._consumer = None
        self._handlers = handlers or []
        self._running = False

    def _init_consumer(self):
        try:
            from confluent_kafka import Consumer
            self._consumer = Consumer({
                "bootstrap.servers": KAFKA_BROKERS,
                "group.id": CONSUMER_GROUP,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 5000,
            })
            self._consumer.subscribe([DETECTION_TOPIC])
            logger.info(f"Detection consumer subscribed to {DETECTION_TOPIC}")
        except ImportError:
            logger.info("confluent-kafka not installed — consumer disabled")
        except Exception as e:
            logger.warning(f"Kafka consumer init failed: {e}")

    def add_handler(self, handler: Callable):
        self._handlers.append(handler)

    def run(self, max_messages: int | None = None):
        self._init_consumer()
        if not self._consumer:
            logger.warning("Consumer not initialized — cannot run")
            return

        self._running = True
        count = 0
        try:
            while self._running:
                msg = self._consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                try:
                    event = json.loads(msg.value().decode("utf-8"))
                    for handler in self._handlers:
                        handler(event)
                    count += 1
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in message: {msg.value()[:100]}")
                except Exception as e:
                    logger.error(f"Handler error: {e}")

                if max_messages and count >= max_messages:
                    break
        finally:
            self._running = False
            if self._consumer:
                self._consumer.close()

    def stop(self):
        self._running = False
