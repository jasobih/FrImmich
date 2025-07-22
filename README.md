# Immich-Frigate Face Sync (Frimmich)

## Overview

**Tired of manually training faces in Frigate? Already spent hours naming everyone in your Immich photo library?**

Frimmich bridges the gap! It provides a web UI to synchronize named faces from your **Immich** instance directly to your **Frigate** NVR's native face recognition system. This allows Frigate to use the high-quality, already-trained faces from your personal photo collection for real-time facial recognition in your CCTV feeds.

**Why do it twice?** Leverage your existing Immich data to speed up your Frigate setup and get more accurate notifications, without the tedious manual work.

This tool acts as the bridge between your photo library and your security system, leveraging Frigate's built-in capabilities.

## How It Works

The application orchestrates a simple data flow:

1.  **Fetch People from Immich:** It connects to your Immich server and fetches all people who have been named.
2.  **Fetch Faces:** For each person, it downloads the cropped thumbnail images of their faces from Immich.
3.  **Save to Frigate Faces Directory:** It saves these cropped face images directly into the designated `known_faces` directory within your Frigate configuration (e.g., `/media/frigate/clips/faces/<person_name>/`). Frigate automatically monitors this directory and uses these images to train its native face recognition models.
4.  **Frigate Recognizes:** Once the images are in place, Frigate uses them to recognize and announce the names of people it detects in your camera feeds.
5.  **Optional Frigate Restart:** After a successful sync, Frimmich can optionally trigger a restart of your Frigate instance via its API, ensuring new faces are loaded immediately.

**Frimmich talks directly to Immich and Frigate's file system/API.**

## Compatibility & Design Philosophy

This application is specifically designed to integrate with **Frigate's native built-in face recognition** (available in Frigate 0.16.0 and later, including Beta 4). It leverages Frigate's ability to automatically train from images placed in a specific directory.

**`Frimmich` is for you if:**
- You are using Frigate 0.16.0+.
- You want to use Frigate's native face recognition.
- You want to easily import already named faces from Immich into Frigate.

**`Frimmich` does NOT use Double Take.** This design moves away from external face recognition services like Double Take, focusing on Frigate's integrated capabilities.

## Complementary Tools: Frigate+ for Enhanced Accuracy

While `Frimmich` handles the crucial task of populating Frigate's known faces database with high-quality, named images from your Immich library, **Frigate+** can further enhance the overall accuracy of your facial recognition system.

Frigate+ is a paid service that offers custom model training, allowing Frigate to become even better at detecting and recognizing faces (and other objects) in your specific camera environments. By improving Frigate's core detection capabilities, Frigate+ indirectly benefits `Frimmich`'s purpose:

-   **Improved Face Detection:** A more accurate Frigate (thanks to Frigate+) will provide better initial face crops, leading to more reliable recognition.
-   **Enhanced Recognition Performance:** When Frigate's underlying models are more finely tuned, the faces trained by `Frimmich` will be recognized with higher confidence and fewer false positives.

In essence, `Frimmich` ensures Frigate *knows who people are* based on your Immich data, while Frigate+ helps Frigate *see and understand faces better* in your unique setup. Together, they provide a powerful and accurate facial recognition solution for your self-hosted NVR.

## Optimizing Face Recognition Accuracy

For optimal performance of Frigate's native face recognition, the *diversity* of the training images is more critical than the sheer *quantity*. Frigate's models are pre-trained to recognize faces, and the images you provide in the `known_faces` directory serve as "anchor" examples for specific identities.

**Key Considerations for Training Images:**

*   **Diversity is Key:** Aim for images that represent the various ways a person might appear in your camera feeds. This includes:
    *   **Different Angles:** Front, side, and three-quarter views.
    *   **Varying Lighting:** Images taken in different lighting conditions (e.g., bright daylight, shadows, low light).
    *   **Different Expressions:** Neutral, smiling, etc.
    *   **Real-world Conditions:** Images that resemble the quality and conditions of your camera feeds (e.g., not just perfect studio shots).
*   **Avoid Redundancy:** Providing many images that are very similar (e.g., all front-facing, well-lit) can lead to overfitting, where the model performs well on ideal images but struggles with the variations found in real camera footage.
*   **Quantity vs. Quality (of Diversity):** While a small number of highly diverse images (e.g., 2-5) can be very effective, a larger set of images (e.g., 20 or more) can also be beneficial *if* those images are genuinely diverse and cover a wide range of appearances. The goal is to provide the model with a comprehensive understanding of the person's appearance under various conditions.

**Leveraging Frimmich for Optimization:**

*   **Curate Immich Faces:** Manually select images in Immich that offer the best diversity for each person.
*   **Control Sync Quantity:** Utilize the `MAX_FACES_PER_PERSON` environment variable in your `docker-compose.yml` or Docker run command to control the maximum number of faces Frimmich syncs for each person. This allows you to experiment with different quantities while prioritizing diversity.
*   **Monitor and Adjust:** After syncing, observe Frigate's recognition performance. If you encounter false positives or negatives, consider refining the selection of images in Immich or adjusting the `MAX_FACES_PER_PERSON` setting.

By focusing on the diversity of your training images, you can significantly enhance the accuracy and robustness of Frigate's face recognition.



## Features

- **Simple Web UI:** A clean interface to trigger and monitor the sync process.
- **One-Click Sync:** A "Sync Now" button to start the process manually.
- **Real-Time Status:** View live updates on the sync progress and see detailed logs.
- **Persistent State:** Remembers which faces have already been synced to avoid redundant training.
- **Containerized:** Runs as a single, self-contained Docker container.
- **Secure:** Designed to run on a private network (like Tailscale), with all sensitive keys managed via environment variables.

## Prerequisites

- **Docker:** You must have Docker installed and running.
- **Immich:** A running Immich instance where you have already named people.
- **Frigate:** A running Frigate instance (version 0.16.0+).
- **Network Access:** Immich and Frigate should be accessible to the `Frimmich` container over the network.
- **Tailscale (Recommended):** For secure and easy network access between your Frimmich container, Immich, and Frigate, especially if they are on different subnets or behind NAT. Using Tailscale simplifies network configuration and avoids complex port forwarding.

## Setup & Configuration

Before running the container, you need to gather the following information:

1.  **Immich API URL & Key:**
    - The URL is typically `http://<immich_ip_or_hostname>:2283`.
    - Get the API Key from your Immich UI: `Account Settings` -> `API Keys` -> `New API Key`.
2.  **Frigate Faces Directory:**
    - This is the absolute path to the `clips/faces` directory within your Frigate media volume.
    - **Example:** If your Frigate `media` volume is mounted at `/mnt/frigate/media`, then the faces directory would be `/mnt/frigate/media/clips/faces`.
    - **Important:** Ensure this directory exists on your host. If not, create it: `mkdir -p /path/to/your/frigate/media/clips/faces`.

### Environment Variables

| Variable                | Description                                                                 | Example                                  |
| ----------------------- | --------------------------------------------------------------------------- | ---------------------------------------- |
| `IMMICH_API_URL`        | **Required.** Base URL of your Immich API.                                  | `http://100.115.110.105:2283`            |
| `IMMICH_API_KEY`        | **Required.** API key for Immich authentication.                            | `your_long_immich_api_key_here`          |
| `FRIGATE_FACES_DIR`     | **Required.** The path *inside the Frimmich container* where Frigate's `clips/faces` directory will be mounted. | `/app/frigate_faces`                     |
| `SKIP_EXISTING_FACES`   | (Optional) `true` or `false`. If `true`, skips faces already synced.        | `true`                                   |
| `UI_PORT`               | (Optional) The internal port for the Flask web server.                      | `8080`                                   |
| `LOG_LEVEL`             | (Optional) Controls log verbosity.                                          | `INFO`                                   |
| `MQTT_HOST`             | (Optional) MQTT Broker Hostname or IP.                                      | `mqtt.local`                             |
| `MQTT_PORT`             | (Optional) MQTT Broker Port.                                                | `1883`                                   |
| `MQTT_USERNAME`         | (Optional) MQTT Username (if authentication is required).                   | `frimmich_user`                          |
| `MQTT_PASSWORD`         | (Optional) MQTT Password.                                                   | `your_mqtt_password`                     |
| `MQTT_TOPIC_PREFIX`     | (Optional) MQTT Topic Prefix for Frimmich messages.                         | `frimmich`                               |
| `FRIGATE_API_URL`       | (Optional) Base URL of your Frigate API (e.g., `http://frigate.local:5000`). Used to trigger restart after sync. | `http://frigate.local:5000`              |
| `SYNC_SCHEDULE_INTERVAL_HOURS` | (Optional) Interval in hours for automatic sync. Set to `0` to disable.    | `24`                                     |
| `MAX_FACES_PER_PERSON`  | (Optional) Maximum number of faces to sync per person.                      | `100`                                    |

## How to Run

### Using Docker Compose (Recommended)

1.  **Create a `docker-compose.yml` file** in your project directory (e.g., `frimmich/docker-compose.yml`):

    ```yaml
    version: '3.8'

    services:
      frimmich:
        image: ghcr.io/jasobih/frimmich:latest # Use pre-built image from GHCR
        container_name: frimmich
        ports:
          - "8080:8080"
        environment:
          # Required Immich Configuration
          - IMMICH_API_URL=http://<your_immich_ip>:2283
          - IMMICH_API_KEY=<your_immich_api_key>
          # Required Frigate Configuration
          - FRIGATE_FACES_DIR=/app/frigate_faces
          # Optional: Scheduled Sync (set to 0 to disable)
          - SYNC_SCHEDULE_INTERVAL_HOURS=0
          # Optional: MQTT Configuration (uncomment and configure to enable)
          # - MQTT_HOST=<your_mqtt_broker_ip>
          # - MQTT_PORT=1883
          # - MQTT_USERNAME=<your_mqtt_username>
          # - MQTT_PASSWORD=<your_mqtt_password>
          # - MQTT_TOPIC_PREFIX=frimmich
          # Optional: Frigate API for restart (uncomment and configure to enable)
          # - FRIGATE_API_URL=http://<your_frigate_ip>:5000
          # Optional: Logging Level (DEBUG, INFO, WARNING, ERROR)
          - LOG_LEVEL=INFO
          # Optional: Max faces per person to sync
          - MAX_FACES_PER_PERSON=100
          # Optional: Skip already existing faces
          - SKIP_EXISTING_FACES=true
        volumes:
          # Persistent storage for synced faces state
          - ./data:/app/data
          # Mount your Frigate clips/faces directory here
          # IMPORTANT: Replace the host path with your actual Frigate faces directory
          - /path/to/your/frigate/media/clips/faces:/app/frigate_faces
        restart: unless-stopped
    ```

2.  **Create a data directory** for `Frimmich`'s persistent state:
    ```bash
    mkdir -p ./data
    ```

3.  **Run Docker Compose** from the same directory as your `docker-compose.yml`:
    ```bash
    docker compose up -d
    ```
    *(This will automatically pull the `ghcr.io/jasobih/frimmich:latest` image and start the container.)*

### Using Docker CLI

1.  **Create a data directory:** Create a directory on your Docker host to store the persistent state file for `Frimmich`.
    ```bash
    mkdir -p /path/to/your/appdata/frimmich
    ```

2.  **Pull the Docker image:**
    ```bash
    docker pull ghcr.io/jasobih/frimmich:latest
    ```

3.  **Run the Docker container:** Use the following command, replacing the placeholder values with your own.

    ```bash
    docker run -d \
      --name frimmich \
      -p 8080:8080 \
      -e "IMMICH_API_URL=http://<your_immich_ip>:2283" \
      -e "IMMICH_API_KEY=<your_immich_api_key>" \
      -e "FRIGATE_FACES_DIR=/app/frigate_faces" \
      -e "SYNC_SCHEDULE_INTERVAL_HOURS=0" \
      -v /path/to/your/appdata/frimmich:/app/data \
      -v /path/to/your/frigate/media/clips/faces:/app/frigate_faces \
      --restart unless-stopped \
      ghcr.io/jasobih/frimmich:latest
    ```

    **Important Volume Mount:** The line `-v /path/to/your/frigate/media/clips/faces:/app/frigate_faces` is crucial. Replace `/path/to/your/frigate/media/clips/faces` with the actual absolute path to your Frigate `clips/faces` directory on your Docker host.

    **Note:** The `-p 8080:8080` maps the container's internal port `8080` to port `8080` on your host machine. You can change the first number (`8080`) to any other available port on your host.

## Usage

1.  Open your web browser and navigate to `http://<your_docker_host_ip>:8080`.
2.  Verify that the Immich URL and Frigate Faces Directory are displayed correctly.
3.  Click the "Sync Now" button to start the synchronization.
4.  Monitor the status and logs in the UI.

## Troubleshooting

- **Cannot connect to Immich:** Double-check the `IMMICH_API_URL`. Ensure there are no firewalls blocking the connection and that the container can reach this IP.
- **Permission Denied when writing faces:** This is a common issue. Ensure the user running the Docker daemon (or the `app` user inside the container, UID/GID 1000) has write permissions to the mounted Frigate faces directory on your host machine. You might need to adjust permissions on the host (e.g., `sudo chown -R 1000:1000 /path/to/your/frigate/media/clips/faces`).
- **401 Unauthorized Error:** Your `IMMICH_API_KEY` is likely incorrect or has been revoked.
