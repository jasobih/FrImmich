import os

class Config:
    IMMICH_API_URL = os.getenv("IMMICH_API_URL")
    IMMICH_API_KEY = os.getenv("IMMICH_API_KEY")
    DOUBLETAKE_API_URL = os.getenv("DOUBLETAKE_API_URL")
    DOUBLETAKE_API_KEY = os.getenv("DOUBLETAKE_API_KEY")
    SKIP_EXISTING_FACES = os.getenv("SKIP_EXISTING_FACES", "true").lower() == "true"
    UI_PORT = int(os.getenv("UI_PORT", "80"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    DATA_DIR = "/app/data"
    STATE_FILE = os.path.join(DATA_DIR, "synced_faces_state.json")
    TEMP_DIR = "/tmp/faces"

    @staticmethod
    def validate():
        if not Config.IMMICH_API_URL or not Config.IMMICH_API_KEY or not Config.DOUBLETAKE_API_URL:
            raise ValueError("Missing required environment variables: IMMICH_API_URL, IMMICH_API_KEY, DOUBLETAKE_API_URL")
