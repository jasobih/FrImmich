import time
import requests
import os
from PIL import Image
from io import BytesIO
from .config import Config
from .state_manager import StateManager

# This function will be the main entry point for the background thread.
def run_sync(app, status_manager):
    with app.app_context(): # Needed to access app.logger
        state_manager = StateManager(Config.STATE_FILE)
        
        try:
            status_manager.add_log("INFO: Starting sync process...")
            status_manager.update_status("Fetching people from Immich...")
            
            # --- 1. Fetch people from Immich ---
            people_url = f"{Config.IMMICH_API_URL}/api/people"
            headers = {"x-api-key": Config.IMMICH_API_KEY, "Accept": "application/json"}
            response = requests.get(people_url, headers=headers)
            response.raise_for_status()
            people = response.json()
            status_manager.add_log(f"INFO: Found {len(people)} people in Immich.")

            trained_count = 0
            skipped_count = 0
            failed_count = 0

            for i, person in enumerate(people):
                person_name = person.get('name', 'Unknown')
                if not person_name:
                    status_manager.add_log(f"WARN: Skipping person with no name (ID: {person['id']}).")
                    continue

                status_manager.update_status(f"Processing {person_name} ({i+1} of {len(people)})...")
                
                # --- 2. Fetch faces for the person ---
                faces_url = f"{Config.IMMICH_API_URL}/api/people/{person['id']}/faces"
                faces_response = requests.get(faces_url, headers=headers)
                faces_response.raise_for_status()
                faces = faces_response.json()

                for face in faces:
                    face_id = face['id']
                    if Config.SKIP_EXISTING_FACES and state_manager.is_synced(face_id):
                        skipped_count += 1
                        continue

                    try:
                        # --- 3. Download, crop, and train ---
                        status_manager.add_log(f"DEBUG: Processing face {face_id} for {person_name}.")
                        asset_id = face['assetId']
                        thumbnail_url = f"{Config.IMMICH_API_URL}/api/asset/{asset_id}/thumbnail"
                        
                        # Download image
                        img_response = requests.get(thumbnail_url, headers=headers, stream=True)
                        img_response.raise_for_status()
                        image = Image.open(BytesIO(img_response.content))

                        # Crop image
                        box = (face['boundingBox']['x1'], face['boundingBox']['y1'], face['boundingBox']['x2'], face['boundingBox']['y2'])
                        cropped_image = image.crop(box)
                        
                        # Save temporarily
                        if not os.path.exists(Config.TEMP_DIR):
                            os.makedirs(Config.TEMP_DIR)
                        temp_path = os.path.join(Config.TEMP_DIR, f"{face_id}.jpg")
                        cropped_image.save(temp_path, "JPEG")

                        # Train Double Take
                        train_url = f"{Config.DOUBLETAKE_API_URL}/api/recognize/train"
                        with open(temp_path, 'rb') as f:
                            files = {'file': (f"{person_name}.jpg", f, 'image/jpeg')}
                            data = {'name': person_name}
                            train_response = requests.post(train_url, files=files, data=data)
                            train_response.raise_for_status()
                        
                        status_manager.add_log(f"INFO: Successfully trained face for {person_name}.")
                        state_manager.add_synced_face(face_id)
                        trained_count += 1

                    except requests.exceptions.RequestException as re:
                        failed_count += 1
                        status_manager.add_log(f"ERROR: Network error while processing face {face_id} for {person_name}: {re}")
                    except Exception as inner_e:
                        failed_count += 1
                        status_manager.add_log(f"ERROR: Failed to process face {face_id} for {person_name}: {inner_e}")
                    finally:
                        # Cleanup temp file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

            summary = {
                "message": f"Sync complete! Trained: {trained_count}, Skipped: {skipped_count}, Failed: {failed_count}.",
                "trained": trained_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "status": "Success" if failed_count == 0 else "Partial Failure"
            }
            status_manager.end_sync(summary)

        except requests.exceptions.RequestException as e:
            error_message = f"Sync Failed: Could not connect to Immich or Double Take. Please check URLs and API keys. Details: {e}"
            status_manager.add_log(f"ERROR: {error_message}")
            summary = {"message": error_message, "status": "Failure"}
            status_manager.end_sync(summary)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            status_manager.add_log(f"CRITICAL: {error_message}")
            summary = {"message": error_message, "status": "Failure"}
            status_manager.end_sync(summary)
