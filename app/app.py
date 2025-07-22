from flask import Flask, render_template, jsonify, request
import threading
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import logging
import requests

from .config import Config
from .status_manager import status_manager
from .sync_logic import run_sync
from .mqtt_client import mqtt_client # Import the MQTT client

# Configure logging for APScheduler
logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__)
    
    # Configure app logging
    app.logger.setLevel(Config.LOG_LEVEL)
    handler = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # Ensure only one handler is added to avoid duplicate logs
    if not app.logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(handler)
        app.logger.addHandler(stream_handler)

    # It's better to validate config when the app starts
    try:
        Config.validate()
    except ValueError as e:
        app.logger.error(f"Configuration error: {e}")
        # In a real app, you might exit or have a dedicated error page
        # For now, we'll just log and let the app start, but it won't function correctly.

    # Initialize scheduler
    scheduler = BackgroundScheduler()
    
    # Function to be scheduled
    def scheduled_sync_job():
        app.logger.info("Attempting scheduled sync...")
        # For scheduled syncs, we process all people (no specific person_ids or max_faces)
        if status_manager.start_sync():
            sync_thread = threading.Thread(target=run_sync, args=(app, status_manager, None, None,))
            sync_thread.start()
        else:
            app.logger.info("Scheduled sync skipped: A sync is already in progress.")

    # Add scheduled job if interval is set
    if Config.SYNC_SCHEDULE_INTERVAL_HOURS > 0:
        scheduler.add_job(
            func=scheduled_sync_job,
            trigger='interval',
            hours=Config.SYNC_SCHEDULE_INTERVAL_HOURS,
            id='scheduled_sync',
            name='Scheduled Immich-Frigate Sync',
            replace_existing=True
        )
        scheduler.start()
        app.logger.info(f"Scheduled sync enabled: every {Config.SYNC_SCHEDULE_INTERVAL_HOURS} hours.")

    # Shut down the scheduler and MQTT client when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    atexit.register(lambda: mqtt_client.disconnect()) # Disconnect MQTT on exit

    @app.route('/')
    def index():
        return render_template('index.html', config=Config)

    @app.route('/api/people')
    def get_people():
        try:
            people_url = f"{Config.IMMICH_API_URL}/api/people"
            headers = {"x-api-key": Config.IMMICH_API_KEY, "Accept": "application/json"}
            response = requests.get(people_url, headers=headers)
            response.raise_for_status()
            return jsonify(response.json())
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error fetching people from Immich: {e}")
            return jsonify({"error": f"Could not fetch people from Immich: {e}"}), 500

    @app.route('/trigger_sync', methods=['POST'])
    def trigger_sync():
        # Expects a list of dictionaries: [{id: "person_id", max_faces: 100}]
        selected_people_data = request.json.get('people', None) 

        if not status_manager.start_sync():
            return jsonify({"error": "Sync already in progress."}), 409

        # Run the sync logic in a background thread, passing selected people data
        sync_thread = threading.Thread(target=run_sync, args=(app, status_manager, selected_people_data,))
        sync_thread.start()
        
        return jsonify({"message": "Sync started."}), 202

    @app.route('/status')
    def get_status():
        return jsonify(status_manager.get_status())

    return app