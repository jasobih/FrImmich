import threading
from collections import deque

class StatusManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.in_progress = False
        self.status_message = "Idle. Last sync: Never"
        self.last_sync_summary = {}
        self.logs = deque(maxlen=100) # Store last 100 log lines

    def start_sync(self):
        with self._lock:
            if self.in_progress:
                return False # Sync already running
            self.in_progress = True
            self.status_message = "Sync initiated..."
            self.logs.clear()
            return True

    def update_status(self, message):
        with self._lock:
            self.status_message = message

    def add_log(self, log_message):
        with self._lock:
            self.logs.append(log_message)

    def end_sync(self, summary):
        with self._lock:
            self.in_progress = False
            self.status_message = summary.get("message", "Sync finished.")
            self.last_sync_summary = summary

    def get_status(self):
        with self._lock:
            return {
                "in_progress": self.in_progress,
                "status_message": self.status_message,
                "last_sync_summary": self.last_sync_summary,
                "logs": list(self.logs)
            }

# Singleton instance
status_manager = StatusManager()
