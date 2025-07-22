import os
import json
import threading

class StateManager:
    def __init__(self, state_file):
        self.state_file = state_file
        self._lock = threading.Lock()
        self.synced_face_ids = self._load_state()

    def _load_state(self):
        with self._lock:
            if not os.path.exists(self.state_file):
                return set()
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('synced_face_ids', []))
            except (IOError, json.JSONDecodeError):
                return set()

    def _save_state(self):
        with self._lock:
            try:
                with open(self.state_file, 'w') as f:
                    json.dump({'synced_face_ids': list(self.synced_face_ids)}, f, indent=2)
            except IOError:
                # Handle potential errors, e.g., log them
                pass

    def is_synced(self, face_id):
        return face_id in self.synced_face_ids

    def add_synced_face(self, face_id):
        with self._lock:
            self.synced_face_ids.add(face_id)
        self._save_state()
