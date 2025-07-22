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
            status_manager.update_status("Sync in progress...")
            
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
            total_faces_processed_overall = 0

            for i, person in enumerate(people):
                person_name = person.get('name', 'Unknown')
                if not person_name:
                    status_manager.add_log(f"WARN: Skipping person with no name (ID: {person['id']}).")
                    continue

                status_manager.update_status(f"Fetching faces for {person_name}...")
                
                # --- 2. Fetch faces for the person ---
                faces_url = f"{Config.IMMICH_API_URL}/api/people/{person['id']}/faces"
                faces_response = requests.get(faces_url, headers=headers)
                faces_response.raise_for_status()
                faces = faces_response.json()

                # Limit faces per person
                faces_to_process = faces[:Config.MAX_FACES_PER_PERSON]
                status_manager.add_log(f"DEBUG: Processing {len(faces_to_process)} faces for {person_name} (max {Config.MAX_FACES_PER_PERSON}).")

                person_faces_processed = 0
                for face in faces_to_process:
                    face_id = face['id']
                    temp_path = None # Initialize temp_path
                    if Config.SKIP_EXISTING_FACES and state_manager.is_synced(face_id):
                        skipped_count += 1
                        person_faces_processed += 1
                        total_faces_processed_overall += 1
                        status_manager.update_progress(person_name, person_faces_processed, len(faces_to_process))
                        continue

                    try:
                        # --- 3. Download, crop, and save to Frigate faces directory ---
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
                        
                        # Save to Frigate faces directory
                        person_dir = os.path.join(Config.FRIGATE_FACES_DIR, person_name)
                        if not os.path.exists(person_dir):
                            os.makedirs(person_dir)
                        
                        output_path = os.path.join(person_dir, f"{face_id}.jpg")
                        cropped_image.save(output_path, "JPEG")
                        
                        status_manager.add_log(f"INFO: Successfully saved face {face_id} for {person_name} to {output_path}.")
                        state_manager.add_synced_face(face_id)
                        trained_count += 1

                    except requests.exceptions.RequestException as re:
                        failed_count += 1
                        status_manager.add_log(f"ERROR: Network error while processing face {face_id} for {person_name}: {re}")
                    except Exception as inner_e:
                        failed_count += 1
                        status_manager.add_log(f"ERROR: Failed to process face {face_id} for {person_name}: {inner_e}")
                    finally:
                        # Cleanup temp file if it was created
                        if temp_path and os.path.exists(temp_path):
                            os.remove(temp_path)
                    
                    person_faces_processed += 1
                    total_faces_processed_overall += 1
                    status_manager.update_progress(person_name, person_faces_processed, len(faces_to_process))

            summary = {
                "message": f"Sync complete! Trained: {trained_count}, Skipped: {skipped_count}, Failed: {failed_count}.",
                "trained": trained_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "status": "Success" if failed_count == 0 else "Partial Failure"
            }
            status_manager.end_sync(summary)

        except requests.exceptions.RequestException as e:
            error_message = f"Sync Failed: Could not connect to Immich. Please check URL and API key. Details: {e}"
            status_manager.add_log(f"ERROR: {error_message}")
            summary = {"message": error_message, "status": "Failure"}
            status_manager.end_sync(summary)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            status_manager.add_log(f"CRITICAL: {error_message}")
            summary = {"message": error_message, "status": "Failure"}
            status_manager.end_sync(summary)