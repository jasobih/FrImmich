# Immich-Frigate Face Sync (Frimmich)

## Overview

Frimmich provides a dedicated web user interface (UI) to facilitate and monitor the synchronization of identified and named faces from an Immich instance to a Frigate facial recognition system (leveraging Double Take for training). It is designed for easy deployment as a single Docker container within a Tailscale network, offering a secure and seamless experience for self-hosted users.

## Features

- **Simple Web UI:** A clean interface to trigger and monitor the sync process.
- **One-Click Sync:** A "Sync Now" button to start the process manually.
- **Real-Time Status:** View live updates on the sync progress and see detailed logs.
- **Persistent State:** Remembers which faces have already been synced to avoid redundant training.
- **Containerized:** Runs as a single, self-contained Docker container.
- **Secure:** Designed to run on a private Tailscale network, and all sensitive keys are managed via environment variables.

## Prerequisites

- **Docker:** You must have Docker installed and running.
- **Immich:** A running Immich instance.
- **Frigate with Double Take:** A running Frigate instance with the Double Take integration configured.
- **Tailscale (Recommended):** All services should be accessible to each other over the network. Tailscale is the recommended way to achieve this securely.

## Setup & Configuration

Before running the container, you need to gather the following information:

1.  **Immich API URL:** The full URL to your Immich instance's API. This is typically `http://<immich_ip_or_hostname>:2283`.
2.  **Immich API Key:**
    - Go to your Immich web UI.
    - Click on your user icon in the top right -> `Account Settings`.
    - Go to `API Keys` -> `New API Key`.
    - Give it a name (e.g., `frimmich-sync`) and click `Create`.
    - Copy the generated key.
3.  **Double Take API URL:** The full URL to your Double Take instance. This is typically `http://<doubletake_ip_or_hostname>:3000`.

### Environment Variables

| Variable                | Description                                                                 | Example                                  |
| ----------------------- | --------------------------------------------------------------------------- | ---------------------------------------- |
| `IMMICH_API_URL`        | **Required.** Base URL of your Immich API.                                  | `http://100.115.110.105:2283`            |
| `IMMICH_API_KEY`        | **Required.** API key for Immich authentication.                            | `your_long_immich_api_key_here`          |
| `DOUBLETAKE_API_URL`    | **Required.** Base URL of your Double Take API.                             | `http://100.115.110.106:3000`            |
| `DOUBLETAKE_API_KEY`    | (Optional) API key for Double Take, if you have one configured.             | `your_doubletake_key`                    |
| `SKIP_EXISTING_FACES`   | (Optional) `true` or `false`. If `true`, skips faces already synced.        | `true`                                   |
| `UI_PORT`               | (Optional) The internal port for the Flask web server.                      | `8080`                                   |
| `LOG_LEVEL`             | (Optional) Controls log verbosity.                                          | `INFO`                                   |

## How to Run

1.  **Create a data directory:** Create a directory on your Docker host to store the persistent state file.
    ```bash
    mkdir -p /path/to/your/appdata/frimmich
    ```

2.  **Run the Docker container:** Use the following command, replacing the placeholder values with your own.

    ```bash
    docker run -d \
      --name frimmich \
      -p 8080:8080 \
      -e "IMMICH_API_URL=http://<your_immich_ip>:2283" \
      -e "IMMICH_API_KEY=<your_immich_api_key>" \
      -e "DOUBLETAKE_API_URL=http://<your_doubletake_ip>:3000" \
      -e "UI_PORT=8080" \
      -v /path/to/your/appdata/frimmich:/app/data \
      --restart unless-stopped \
      ghcr.io/your-username/frimmich:latest # Replace with the final image name
    ```

    **Note:** The `-p 8080:8080` maps the container's internal port `8080` to port `8080` on your host machine. You can change the first number (`8080`) to any other available port on your host.

## Usage

1.  Open your web browser and navigate to `http://<your_docker_host_ip>:8080`.
2.  Verify that the Immich and Double Take URLs are displayed correctly.
3.  Click the "Sync Now" button to start the synchronization.
4.  Monitor the status and logs in the UI.

## Troubleshooting

- **Cannot connect to Immich/Double Take:** Double-check the `IMMICH_API_URL` and `DOUBLETAKE_API_URL`. Ensure there are no firewalls blocking the connection and that the container can reach these IPs.
- **Permission Denied on `/app/data`:** Check the permissions of the host directory you are mounting as a volume (`/path/to/your/appdata/frimmich`). The user running the Docker daemon needs write access.
- **401 Unauthorized Error:** Your `IMMICH_API_KEY` is likely incorrect or has been revoked.
