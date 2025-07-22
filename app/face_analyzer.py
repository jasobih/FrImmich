import os
import requests
from PIL import Image
from io import BytesIO
import numpy as np
import dlib
import face_recognition
from skimage.filters import laplacian
from scipy.spatial.distance import euclidean

from .config import Config

# Initialize dlib's face detector and shape predictor
# You'll need to download shape_predictor_68_face_landmarks.dat
# from http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
# and place it in a known location, e.g., next to this file or in a 'models' directory.
# For simplicity, let's assume it's in the same directory for now.
# In a production environment, manage this model file properly.
try:
    face_detector = dlib.get_frontal_face_detector()
    # Path to the dlib shape predictor model
    shape_predictor_path = os.path.join(os.path.dirname(__file__), "shape_predictor_68_face_landmarks.dat")
    face_pose_predictor = dlib.shape_predictor(shape_predictor_path)
    face_encoder = face_recognition.face_encodings # Uses dlib internally
except Exception as e:
    print(f"Error loading dlib models: {e}. Please ensure 'shape_predictor_68_face_landmarks.dat' is available.")
    face_detector = None
    face_pose_predictor = None
    face_encoder = None


def download_image(url, api_key, logger):
    """Downloads an image from a URL."""
    try:
        headers = {"x-api-key": api_key}
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading image from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing image from {url}: {e}")
        return None

def analyze_face_quality(face_image, logger):
    """Analyzes clarity, frontal angle, and basic lighting for a single face image."""
    if face_image is None:
        return 0, 0, 0 # clarity, frontal_score, lighting_score

    # Convert to grayscale for some analyses
    gray_image = face_image.convert("L")
    np_image = np.array(face_image)
    np_gray_image = np.array(gray_image)

    # 1. Clarity (using Laplacian variance)
    # Higher variance indicates more detail/sharpness
    clarity = laplacian(np_gray_image).var()

    # 2. Frontal Angle (using dlib's pose predictor)
    frontal_score = 0
    try:
        # dlib expects RGB image for face detection
        faces_rects = face_detector(np_image, 1)
        if len(faces_rects) > 0:
            # Assuming only one face per cropped image for simplicity
            shape = face_pose_predictor(np_image, faces_rects[0])
            
            # Calculate head pose (simplified: just yaw and pitch)
            # This requires more advanced 3D pose estimation, but for a simple score:
            # We can look at the symmetry of landmarks or use a pre-trained pose estimator.
            # For now, a very basic heuristic: assume more frontal if landmarks are symmetric.
            # A more accurate frontal score would involve calculating yaw/pitch/roll
            # and scoring based on how close they are to zero.
            # For example, using solvePnP with 3D model points and 2D image points.

            left_eye_x = shape.part(36).x
            right_eye_x = shape.part(45).x
            nose_tip_x = shape.part(30).x
            
            # If nose tip is roughly centered between eyes, it's more frontal
            if left_eye_x < nose_tip_x < right_eye_x:
                frontal_score = 1.0 # Placeholder for truly frontal
            else:
                frontal_score = 0.5 # Some angle
            

    except Exception as e:
        logger.warning(f"Error in dlib face pose prediction: {e}")
        frontal_score = 0 # Cannot determine frontal angle

    # 3. Lighting (simple average brightness)
    # This is very basic; more advanced would be uniformity, highlights/shadows.
    lighting_score = np_gray_image.mean() / 255.0 # Normalize to 0-1

    return clarity, frontal_score, lighting_score

def analyze_and_suggest_faces(all_person_faces, logger, num_suggestions=5, max_faces_to_analyze=50):
    """
    Analyzes a list of face objects and suggests the best ones for training.
    
    Args:
        all_person_faces (list): List of face dictionaries from Immich API.
        logger: Logger object for logging messages.
        num_suggestions (int): Number of best faces to suggest.
        max_faces_to_analyze (int): Maximum number of faces to analyze for resource management.
    
    Returns:
        list: A list of suggested face IDs.
    """
    if not face_detector or not face_pose_predictor or not face_encoder:
        logger.error("Dlib models not loaded. Cannot perform smart face analysis.")
        return []

    logger.info(f"Starting smart face analysis for {len(all_person_faces)} faces (analyzing up to {max_faces_to_analyze})...")
    
    analyzed_faces = []
    face_embeddings = []
    
    # Limit the number of faces to analyze to manage resources
    faces_for_analysis = all_person_faces[:max_faces_to_analyze]

    for i, face_data in enumerate(faces_for_analysis):
        face_id = face_data['id']
        thumbnail_url = face_data['thumbnailUrl'] # Use the thumbnail for analysis to save bandwidth/time

        logger.info(f"Analyzing face {i+1}/{len(faces_for_analysis)}: {face_id}")
        
        # Download the face image
        face_image_pil = download_image(thumbnail_url, Config.IMMICH_API_KEY, logger)
        if face_image_pil is None:
            logger.warning(f"Skipping face {face_id} due to download error.")
            continue

        # Convert PIL Image to numpy array (RGB) for dlib/face_recognition
        face_image_np = np.array(face_image_pil)

        # Get face embeddings
        # face_recognition.face_encodings expects a full image, then finds faces.
        # Since we already have cropped faces, we can pass the cropped image directly.
        # However, face_recognition.face_encodings internally runs detection.
        # For a pre-cropped face, we might need to adjust or ensure it's treated as the only face.
        
        # A more direct way if we are sure it's a single face:
        # embeddings = face_recognition.face_encodings(face_image_np, known_face_locations=[(0, face_image_np.shape[1], face_image_np.shape[0], 0)])
        # For simplicity, let's just run face_encodings on the image, assuming it finds the main face.
        
        embeddings = face_encoder(face_image_np)
        if len(embeddings) == 0:
            logger.warning(f"No face found in image for {face_id} by face_recognition. Skipping.")
            continue
        
        face_embedding = embeddings[0] # Take the first (and hopefully only) face found

        # Analyze quality metrics
        clarity, frontal_score, lighting_score = analyze_face_quality(face_image_pil, logger)

        analyzed_faces.append({
            'id': face_id,
            'embedding': face_embedding,
            'clarity': clarity,
            'frontal_score': frontal_score,
            'lighting_score': lighting_score
        })
        face_embeddings.append(face_embedding)

    if not analyzed_faces:
        logger.info("No faces successfully analyzed.")
        return []

    # Calculate scores and select diverse faces
    suggested_face_ids = []
    
    # Simple scoring: prioritize clarity, then frontal, then lighting.
    # Dissimilarity will be handled during selection.
    for face in analyzed_faces:
        # Normalize clarity and lighting if necessary (e.g., to 0-1 range)
        # For now, just use raw values, assuming higher is better.
        face['overall_score'] = (face['clarity'] * 0.4) + (face['frontal_score'] * 0.4) + (face['lighting_score'] * 0.2)
    
    # Sort by overall score (descending)
    analyzed_faces.sort(key=lambda x: x['overall_score'], reverse=True)

    # Select top N diverse faces
    selected_embeddings = []
    for face in analyzed_faces:
        if len(suggested_face_ids) >= num_suggestions:
            break
        
        is_diverse_enough = True
        if selected_embeddings:
            # Check similarity to already selected faces
            for existing_embedding in selected_embeddings:
                distance = euclidean(face['embedding'], existing_embedding)
                # A higher distance means less similar. Adjust threshold as needed.
                if distance < 0.6: # Example threshold: faces too similar
                    is_diverse_enough = False
                    break
        
        if is_diverse_enough:
            suggested_face_ids.append(face['id'])
            selected_embeddings.append(face['embedding'])
            logger.info(f"Selected face {face['id']} (Score: {face['overall_score']:.2f}, Clarity: {face['clarity']:.2f}, Frontal: {face['frontal_score']:.2f}, Lighting: {face['lighting_score']:.2f})")

    logger.info(f"Smart face analysis complete. Suggested {len(suggested_face_ids)} faces.")
    return suggested_face_ids