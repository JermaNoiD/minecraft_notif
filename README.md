# Minecraft Server Player Join/Leave Notification System

![Docker Pulls](https://img.shields.io/docker/pulls/jermanoid/minecraft_notif)
![GitHub](https://img.shields.io/github/license/jermanoid/minecraft_notif)

[Dockerhub](https://hub.docker.com/r/jermanoid/minecraft_notif)

A lightweight Dockerized application that monitors a Minecraft server log file and sends notifications for player join, leave, and whitelist failure events. Supports **ntfy** and **Discord** notification services with configurable toggles and custom notification titles.

The image is available on Docker Hub as `jermanoid/minecraft_notif:latest`

## Features
- Monitors Minecraft server logs for player events (join, leave, whitelist failures)
- Supports notifications via **ntfy** or **Discord** webhooks
- Configurable via environment variables
- Toggles for enabling/disabling specific event notifications
- Customizable notification subject/title
- Lightweight image based on `python:3.9-slim`
- Easy deployment with Docker Compose

## Prerequisites
- Docker and Docker Compose installed
- A Minecraft server with accessible log files (e.g., `/logs/latest.log`)
- For NTFY: An ntfy topic and an [access token](https://docs.ntfy.sh/config/#access-tokens)
- For Discord: A Discord webhook URL

## Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/jermanoid/minecraft_notif.git
   cd minecraft_notif
   ```
2. **Create the .env file**
   ```bash
   cp .env.example .env
   ```
3. **Modify the .env file for your needs**
   ```bash
   nano .env```
   ```
   ```
   # Notification service (ntfy or discord)
   NOTIFY_SERVICE=ntfy
   # Required for ntfy
   NTFY_TOPIC=your_ntfy_topic
   # Optional for ntfy
   NTFY_URL=https://ntfy.sh
   NTFY_TOKEN=your_ntfy_token
   # Required for discord
   DISCORD_WEBHOOK_URL=your_discord_webhook_url
   # Notification subject
   NOTIFY_SUBJECT=My Awesome Minecraft Server
   # Notification toggles (true/false)
   NOTIFY_JOIN=true
   NOTIFY_LEAVE=true
   NOTIFY_WHITELIST=true
   ```
5. **Modify the docker-compose.yaml file and update your volume directory**
   
   locate your minecraft logs directory. When you list the files in the directory you should see "lastest.log" This is the directory to use
   ```bash
   nano docker-compose.yml
   ```
   ```
   services:

   minecraft-notif:
    container_name: minecraft-notif
    environment:
      - LOG_FILE=/logs/latest.log
      - NOTIFY_SERVICE=${NOTIFY_SERVICE:-ntfy}
      - NTFY_TOPIC=${NTFY_TOPIC}
      - NTFY_URL=${NTFY_URL:-https://ntfy.sh}
      - NTFY_TOKEN=${NTFY_TOKEN}
      - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
      - NOTIFY_SUBJECT=${NOTIFY_SUBJECT:-Minecraft Server}
      - NOTIFY_JOIN=${NOTIFY_JOIN:-true}
      - NOTIFY_LEAVE=${NOTIFY_LEAVE:-true}
      - NOTIFY_WHITELIST=${NOTIFY_WHITELIST:-true}
    image: minecraft_notif:latest
    restart: always
    volumes:
        #update this path preceeding the colon to the path of your logs directory that contains "latest.log"
        - /path/to/logs/directory:/logs:ro
   ```
7. **Run the compose**
   ```bash
   docker compose up -d
   ```

8. **Test logging in**
   Try logging into your Minecraft server and if your volume directory and environment variables are set properly you should receive a notification.
