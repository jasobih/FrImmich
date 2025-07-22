import os

class Config:
    IMMICH_API_URL = os.getenv("IMMICH_API_URL")
    IMMICH_API_KEY = os.getenv("IMMICH_API_KEY")
    FRIGATE_FACES_DIR = os.getenv("FRIGATE_FACES_DIR", "/app/frigate_faces")
    SKIP_EXISTING_FACES = os.getenv("SKIP_EXISTING_FACES", "true").lower() == "true"
    UI_PORT = int(os.getenv("UI_PORT", "8080"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    DATA_DIR = "/app/data"
    STATE_FILE = os.path.join(DATA_DIR, "synced_faces_state.json")
    TEMP_DIR = "/tmp/faces"
    MAX_FACES_PER_PERSON = int(os.getenv("MAX_FACES_PER_PERSON", "100"))
    SYNC_SCHEDULE_INTERVAL_HOURS = int(os.getenv("SYNC_SCHEDULE_INTERVAL_HOURS", "0"))

    # MQTT Configuration
    MQTT_HOST = os.getenv("MQTT_HOST")
    MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_USERNAME = os.getenv("MQTT_USERNAME")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
    MQTT_TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "frimmich")

    # Frigate API for restart
    FRIGATE_API_URL = os.getenv("FRIGATE_API_URL") # Base URL for Frigate API (e.g., http://frigate.local:5000)

    @staticmethod
    def validate():
        if not Config.IMMICH_API_URL or not Config.IMMICH_API_KEY or not Config.FRIGATE_FACES_DIR:
            raise ValueError("Missing required environment variables: IMMICH_API_URL, IMMICH_API_KEY, FRIGATE_FACES_DIR")