from flask import Flask, render_template, jsonify, request
import threading
from .config import Config
from .status_manager import status_manager
from .sync_logic import run_sync

def create_app():
    app = Flask(__name__)
    
    # It's better to validate config when the app starts
    try:
        Config.validate()
    except ValueError as e:
        # If config is invalid, we can't run. Log and exit.
        app.logger.error(f"Configuration error: {e}")
        # In a real app, you might exit or have a dedicated error page

    @app.route('/')
    def index():
        return render_template('index.html', config=Config)

    @app.route('/trigger_sync', methods=['POST'])
    def trigger_sync():
        if not status_manager.start_sync():
            return jsonify({"error": "Sync already in progress."}), 409

        # Run the sync logic in a background thread
        sync_thread = threading.Thread(target=run_sync, args=(app, status_manager,))
        sync_thread.start()
        
        return jsonify({"message": "Sync started."}), 202

    @app.route('/status')
    def get_status():
        return jsonify(status_manager.get_status())

    return app
