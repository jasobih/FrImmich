import paho.mqtt.client as mqtt
import json
import logging
from .config import Config

logger = logging.getLogger(__name__)

class MQTTClient:
    _instance = None
    _client = None
    _is_connected = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MQTTClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        if not Config.MQTT_HOST:
            logger.info("MQTT_HOST not set. MQTT client will not be initialized.")
            return

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish

        if Config.MQTT_USERNAME and Config.MQTT_PASSWORD:
            self._client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)

        try:
            logger.info(f"Attempting to connect to MQTT broker at {Config.MQTT_HOST}:{Config.MQTT_PORT}")
            self._client.connect(Config.MQTT_HOST, Config.MQTT_PORT, 60)
            self._client.loop_start() # Start a non-blocking loop
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._is_connected = True
            logger.info("Connected to MQTT Broker!")
            self.publish_status("online")
        else:
            logger.error(f"Failed to connect, return code {rc}\n")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self._is_connected = False
        logger.warning(f"Disconnected from MQTT Broker with code {rc}")

    def _on_publish(self, client, userdata, mid, properties=None):
        logger.debug(f"Message {mid} published.")

    def publish(self, topic_suffix, payload, retain=False):
        if not self._is_connected:
            logger.warning(f"Not connected to MQTT. Cannot publish to {topic_suffix}.")
            return
        
        full_topic = f"{Config.MQTT_TOPIC_PREFIX}/{topic_suffix}"
        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            self._client.publish(full_topic, payload, qos=1, retain=retain)
            logger.debug(f"Published to {full_topic}: {payload}")
        except Exception as e:
            logger.error(f"Error publishing to MQTT topic {full_topic}: {e}")

    def publish_status(self, status_message):
        self.publish("status", status_message, retain=True)

    def publish_sync_progress(self, progress_data):
        self.publish("sync_progress", progress_data)

    def publish_sync_summary(self, summary_data):
        self.publish("sync_summary", summary_data)

    def disconnect(self):
        if self._client:
            self.publish_status("offline")
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("Disconnected from MQTT broker.")

mqtt_client = MQTTClient()
