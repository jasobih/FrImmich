from flask import Flask, render_template, jsonify, request
import threading
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import logging

from .config import Config
from .status_manager import status_manager
from .sync_logic import run_sync

# Configure logging for APScheduler
logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__)
    
    # Configure app logging
    app.logger.setLevel(Config.LOG_LEVEL)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

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
        if status_manager.start_sync():
            sync_thread = threading.Thread(target=run_sync, args=(app, status_manager,))
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

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

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
