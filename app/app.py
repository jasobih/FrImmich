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
from . import face_analyzer # Import the new face_analyzer module

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

    @app.route('/api/people/<person_id>/faces')
    def get_person_faces(person_id):
        try:
            # Allow fetching all faces for analysis, or paginated for display
            fetch_all = request.args.get('all', 'false').lower() == 'true'
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('pageSize', 20, type=int) # Default to 20 faces per page

            assets_url = f"{Config.IMMICH_API_URL}/api/assets?personId={person_id}"
            headers = {"x-api-key": Config.IMMICH_API_KEY, "Accept": "application/json"}
            assets_response = requests.get(assets_url, headers=headers)
            assets_response.raise_for_status()
            assets = assets_response.json()

            all_faces = []
            for asset in assets:
                asset_id = asset.get('id')
                if not asset_id:
                    continue

                asset_detail_url = f"{Config.IMMICH_API_URL}/api/assets/{asset_id}"
                asset_detail_response = requests.get(asset_detail_url, headers=headers)
                asset_detail_response.raise_for_status()
                asset_detail = asset_detail_response.json()

                if 'faces' in asset_detail:
                    for face in asset_detail['faces']:
                        if face.get('personId') == person_id:
                            all_faces.append({
                                'id': face.get('id'),
                                'assetId': face.get('assetId'), # Ensure assetId is present in face object
                                'personId': face.get('personId'),
                                'boundingBox': face.get('boundingBox'),
                                'thumbnailUrl': f"{Config.IMMICH_API_URL}/api/faces/{face.get('id')}/thumbnail"
                            })
            
            if fetch_all:
                return jsonify(all_faces)

            total_faces = len(all_faces)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_faces = all_faces[start_index:end_index]

            return jsonify({
                "faces": paginated_faces,
                "totalFaces": total_faces,
                "page": page,
                "pageSize": page_size
            })
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error fetching faces for person {person_id} from Immich: {e}")
            return jsonify({"error": f"Could not fetch faces for person {person_id} from Immich: {e}"}), 500

    @app.route('/api/people/<person_id>/suggest_faces')
    def suggest_faces(person_id):
        app.logger.info(f"Attempting to suggest faces for person {person_id}")
        try:
            # Fetch all faces for the person (up to a limit for analysis)
            # We'll use a higher page_size or a dedicated internal call to get more faces for analysis
            # For now, let's assume we fetch all and face_analyzer will handle the limit
            # In a real scenario, we might want to fetch only the first N faces from Immich
            # to avoid excessive resource usage if a person has thousands of faces.
            # For this iteration, we'll fetch all and let the analyzer limit.
            faces_response = requests.get(f"{Config.IMMICH_API_URL}/api/people/{person_id}/faces?all=true", headers={"x-api-key": Config.IMMICH_API_KEY, "Accept": "application/json"})
            faces_response.raise_for_status()
            all_person_faces = faces_response.json()

            if not all_person_faces:
                return jsonify({"message": "No faces found for analysis.", "suggested_face_ids": []}), 200

            # Call the face_analyzer to get suggested faces
            # This will be a blocking call, consider threading for very long analysis
            suggested_face_ids = face_analyzer.analyze_and_suggest_faces(all_person_faces, app.logger)
            
            return jsonify({"suggested_face_ids": suggested_face_ids}), 200

        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error fetching faces from Immich for analysis: {e}")
            return jsonify({"error": f"Could not fetch faces from Immich for analysis: {e}"}), 500
        except Exception as e:
            app.logger.error(f"Error during face analysis for person {person_id}: {e}")
            return jsonify({"error": f"Error during face analysis: {e}"}), 500

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