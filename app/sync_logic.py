import time
import requests
import os
from PIL import Image
from io import BytesIO
from .config import Config
from .state_manager import StateManager
from .mqtt_client import mqtt_client # Import the MQTT client

# This function will be the main entry point for the background thread.
def run_sync(app, status_manager, selected_people_data=None):
    with app.app_context(): # Needed to access app.logger
        state_manager = StateManager(Config.STATE_FILE)
        
        try:
            status_manager.add_log("INFO: Starting sync process...")
            status_manager.update_status("Sync in progress...")
            mqtt_client.publish_status("sync_in_progress")
            
            # --- 1. Fetch people from Immich ---
            people_url = f"{Config.IMMICH_API_URL}/api/people"
            headers = {"x-api-key": Config.IMMICH_API_KEY, "Accept": "application/json"}
            response = requests.get(people_url, headers=headers)
            response.raise_for_status()
            all_people = response.json()
            status_manager.add_log(f"INFO: Found {len(all_people)} people in Immich.")

            # Prepare people to process based on selection and global config
            people_to_process_data = []
            if selected_people_data is not None: # Manual sync with selection (curated faces)
                # selected_people_data is now [{id: "person_id", faces: ["face_id_1", "face_id_2"]}]
                people_to_process_data = selected_people_data
                status_manager.add_log(f"INFO: Syncing {len(people_to_process_data)} selected people with curated faces.")
            else: # Scheduled sync or manual sync without selection (sync all with MAX_FACES_PER_PERSON)
                for p in all_people:
                    # For non-curated syncs, we still fetch all faces and then limit
                    people_to_process_data.append({'id': p['id'], 'name': p.get('name', 'Unknown'), 'faces': []}) # 'faces' will be populated later

                status_manager.add_log(f"INFO: Syncing all {len(people_to_process_data)} people (non-curated).")

            trained_count = 0
            skipped_count = 0
            failed_count = 0
            total_faces_processed_overall = 0

            for i, person_data in enumerate(people_to_process_data):
                person_id = person_data['id']
                person_name = next((p.get('name', 'Unknown') for p in all_people if p['id'] == person_id), 'Unknown')
                curated_face_ids = person_data.get('faces') # This will be None for non-curated syncs

                if not person_name:
                    status_manager.add_log(f"WARN: Skipping person with no name (ID: {person_id}).")
                    continue

                status_manager.update_status(f"Fetching faces for {person_name}...")
                
                # --- 2. Fetch all faces for the person from Immich ---
                # We need to fetch all faces to get their bounding box and assetId,
                # then filter by curated_face_ids if provided.
                all_person_faces_url = f"{Config.IMMICH_API_URL}/api/people/{person_id}/faces"
                all_person_faces_response = requests.get(all_person_faces_url, headers=headers)
                all_person_faces_response.raise_for_status()
                all_person_faces = all_person_faces_response.json()

                faces_to_process = []
                if curated_face_ids is not None and len(curated_face_ids) > 0:
                    # Filter for only the curated faces
                    faces_to_process = [face for face in all_person_faces if face['id'] in curated_face_ids]
                    status_manager.add_log(f"DEBUG: Processing {len(faces_to_process)} curated faces for {person_name}.")
                else:
                    # Non-curated sync: apply MAX_FACES_PER_PERSON limit
                    faces_to_process = all_person_faces[:Config.MAX_FACES_PER_PERSON]
                    status_manager.add_log(f"DEBUG: Processing {len(faces_to_process)} faces for {person_name} (limited by MAX_FACES_PER_PERSON).")

                person_faces_processed = 0
                for face in faces_to_process:
                    face_id = face['id']
                    temp_path = None # Initialize temp_path
                    if Config.SKIP_EXISTING_FACES and state_manager.is_synced(face_id):
                        skipped_count += 1
                        person_faces_processed += 1
                        total_faces_processed_overall += 1
                        status_manager.update_progress(person_name, person_faces_processed, len(faces_to_process))
                        mqtt_client.publish_sync_progress(status_manager.get_status())
                        continue

                    try:
                        # --- 3. Download, crop, and save to Frigate faces directory ---
                        status_manager.add_log(f"DEBUG: Processing face {face_id} for {person_name}.")
                        # The thumbnail URL for a specific face is directly from the /api/faces/{id}/thumbnail endpoint
                        thumbnail_url = f"{Config.IMMICH_API_URL}/api/faces/{face_id}/thumbnail"
                        
                        # Download image
                        img_response = requests.get(thumbnail_url, headers=headers, stream=True)
                        img_response.raise_for_status()
                        image = Image.open(BytesIO(img_response.content))

                        # Crop image using bounding box from the face object
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
                    mqtt_client.publish_sync_progress(status_manager.get_status())

            summary = {
                "message": f"Sync complete! Trained: {trained_count}, Skipped: {skipped_count}, Failed: {failed_count}.",
                "trained": trained_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "status": "Success" if failed_count == 0 else "Partial Failure"
            }
            status_manager.end_sync(summary)
            mqtt_client.publish_sync_summary(summary)
            mqtt_client.publish_status("idle")

            # --- Trigger Frigate Restart if configured ---
            if Config.FRIGATE_API_URL:
                status_manager.add_log("INFO: Triggering Frigate restart to load new faces...")
                try:
                    frigate_restart_url = f"{Config.FRIGATE_API_URL}/api/restart"
                    restart_response = requests.post(frigate_restart_url)
                    restart_response.raise_for_status()
                    status_manager.add_log("INFO: Frigate restart command sent successfully.")
                except requests.exceptions.RequestException as re:
                    status_manager.add_log(f"ERROR: Failed to trigger Frigate restart: {re}")
                except Exception as e:
                    status_manager.add_log(f"ERROR: An unexpected error occurred during Frigate restart: {e}")

        except requests.exceptions.RequestException as e:
            error_message = f"Sync Failed: Could not connect to Immich. Please check URL and API key. Details: {e}"
            status_manager.add_log(f"ERROR: {error_message}")
            summary = {"message": error_message, "status": "Failure"}
            status_manager.end_sync(summary)
            mqtt_client.publish_sync_summary(summary)
            mqtt_client.publish_status("error")
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            status_manager.add_log(f"CRITICAL: {error_message}")
            summary = {"message": error_message, "status": "Failure"}
            status_manager.end_sync(summary)
            mqtt_client.publish_sync_summary(summary)
            mqtt_client.publish_status("error")