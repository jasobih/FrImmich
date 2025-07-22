# Changelog

## 0.1.3 - 2025-07-23

### Added
- **Smart Face Trainer (Opt-in):** Introduced an opt-in feature within the face curation UI to automatically suggest the "best" 5-10 diverse faces for a person from their Immich library. This leverages computer vision to analyze clarity, frontal angle, lighting, and dissimilarity, aiming to provide optimal training images for Frigate while managing resource usage by analyzing a limited subset of photos.
- **Face Curation UI:** Implemented a new web UI feature allowing users to manually select specific faces from Immich to sync to Frigate. This provides fine-grained control over the training data, addressing recommendations for diverse and limited training sets.
- New API endpoint `/api/people/<person_id>/faces` to fetch all detected faces for a given person from Immich.
- New API endpoint `/api/people/<person_id>/suggest_faces` to trigger the smart face analysis.

### Changed
- **Face Curation UI:** Implemented pagination and a "Load More" button for the face curation modal, improving usability and performance when a person has a large number of faces.
- **Sync Logic:** Updated `sync_logic.py` to utilize the curated face selections. The `MAX_FACES_PER_PERSON` environment variable now acts as a default for non-curated syncs, but is overridden by user selections.
- **README.md:** Revised the "Optimizing Face Recognition Accuracy" section to emphasize the importance of diversity in training images over strict quantity, and to guide users on leveraging the new curation feature.

### Removed
- Removed `version` specification from `docker-compose.yml` for better compatibility.

### Fixed
- N/A

## 0.1.4 - 2025-07-23

### Fixed
- Dockerfile: Added `cmake` and `build-essential` packages to ensure successful compilation of `dlib` and `face_recognition` during Docker image build.

## 0.1.5 - 2025-07-23

### Fixed
- Dockerfile: Added `libboost-python-dev`, `libboost-thread-dev`, `libx11-dev`, and `libatlas-base-dev` to further support `dlib` compilation.

## 0.1.6 - 2025-07-23

### Removed
- **Smart Face Trainer Feature:** Reverted the opt-in Smart Face Trainer feature, including `app/face_analyzer.py`, related API endpoints, UI elements, and build dependencies (`dlib`, `face_recognition`, `scikit-image`) due to persistent Docker build issues with `dlib` compilation.
