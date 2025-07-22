import threading
from collections import deque

class StatusManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.in_progress = False
        self.status_message = "Idle. Last sync: Never"
        self.last_sync_summary = {}
        self.logs = deque(maxlen=100) # Store last 100 log lines
        self.current_person = ""
        self.processed_faces_count = 0
        self.total_faces_to_process = 0

    def start_sync(self):
        with self._lock:
            if self.in_progress:
                return False # Sync already running
            self.in_progress = True
            self.status_message = "Sync initiated..."
            self.logs.clear()
            self.current_person = ""
            self.processed_faces_count = 0
            self.total_faces_to_process = 0
            return True

    def update_status(self, message):
        with self._lock:
            self.status_message = message

    def update_progress(self, current_person, processed_faces_count, total_faces_to_process):
        with self._lock:
            self.current_person = current_person
            self.processed_faces_count = processed_faces_count
            self.total_faces_to_process = total_faces_to_process
            if total_faces_to_process > 0:
                progress_percent = (processed_faces_count / total_faces_to_process) * 100
                self.status_message = f"Processing {current_person} ({processed_faces_count}/{total_faces_to_process} faces) - {progress_percent:.1f}%"
            else:
                self.status_message = f"Processing {current_person} (0/0 faces)"

    def add_log(self, log_message):
        with self._lock:
            self.logs.append(log_message)

    def end_sync(self, summary):
        with self._lock:
            self.in_progress = False
            self.status_message = summary.get("message", "Sync finished.")
            self.last_sync_summary = summary
            self.current_person = ""
            self.processed_faces_count = 0
            self.total_faces_to_process = 0

    def get_status(self):
        with self._lock:
            return {
                "in_progress": self.in_progress,
                "status_message": self.status_message,
                "last_sync_summary": self.last_sync_summary,
                "logs": list(self.logs),
                "current_person": self.current_person,
                "processed_faces_count": self.processed_faces_count,
                "total_faces_to_process": self.total_faces_to_process
            }

# Singleton instance
status_manager = StatusManager()