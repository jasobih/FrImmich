# Changelog

## 0.1.1 - 2025-07-23

### Added
- **Face Curation UI:** Implemented a new web UI feature allowing users to manually select specific faces from Immich to sync to Frigate. This provides fine-grained control over the training data, addressing recommendations for diverse and limited training sets.
- New API endpoint `/api/people/<person_id>/faces` to fetch all detected faces for a given person from Immich.

### Changed
- **Face Curation UI:** Implemented pagination and a "Load More" button for the face curation modal, improving usability and performance when a person has a large number of faces.
- **Sync Logic:** Updated `sync_logic.py` to utilize the curated face selections. The `MAX_FACES_PER_PERSON` environment variable now acts as a default for non-curated syncs, but is overridden by user selections.
- **README.md:** Revised the "Optimizing Face Recognition Accuracy" section to emphasize the importance of diversity in training images over strict quantity, and to guide users on leveraging the new curation feature.

### Removed
- Removed `version` specification from `docker-compose.yml` for better compatibility.

### Fixed
- N/A
