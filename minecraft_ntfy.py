import re
import time
import requests
import os
import logging
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
LOG_FILE = os.getenv('LOG_FILE', '/logs/latest.log')
NOTIFY_SERVICE = os.getenv('NOTIFY_SERVICE', 'ntfy').lower()  # 'ntfy' or 'discord'
NTFY_TOPIC = os.getenv('NTFY_TOPIC')
NTFY_URL = os.getenv('NTFY_URL', 'https://ntfy.sh')
NTFY_TOKEN = os.getenv('NTFY_TOKEN')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
NOTIFY_SUBJECT = os.getenv('NOTIFY_SUBJECT', 'Minecraft Server')  # Title for notifications
NOTIFY_JOIN = os.getenv('NOTIFY_JOIN', 'true').lower() == 'true'
NOTIFY_LEAVE = os.getenv('NOTIFY_LEAVE', 'true').lower() == 'true'
NOTIFY_WHITELIST = os.getenv('NOTIFY_WHITELIST', 'true').lower() == 'true'

# Regex patterns for join/leave/whitelist events
JOIN_PATTERN = re.compile(r"\[Server thread/INFO\]: (\w+) joined the game")
LEAVE_PATTERN = re.compile(r"\[Server thread/INFO\]: (\w+) left the game")
WHITELIST_PATTERN = re.compile(r"\[Server thread/INFO\]: (\w+) was kicked due to: You are not white-listed on this server!")

def validate_config() -> bool:
    """Validate required environment variables based on notification service."""
    # Common required variables
    if not LOG_FILE:
        logger.error("Missing required environment variable: LOG_FILE")
        return False
    
    if not Path(LOG_FILE).parent.exists():
        logger.error(f"Log file directory does not exist: {Path(LOG_FILE).parent}")
        return False

    if not NOTIFY_SUBJECT:
        logger.error("NOTIFY_SUBJECT cannot be empty")
        return False

    # Service-specific validation
    if NOTIFY_SERVICE == 'ntfy':
        if not NTFY_TOPIC:
            logger.error("Missing required environment variable: NTFY_TOPIC")
            return False
        if not NTFY_URL.startswith(('http://', 'https://')):
            logger.error("NTFY_URL must start with http:// or https://")
            return False
    elif NOTIFY_SERVICE == 'discord':
        if not DISCORD_WEBHOOK_URL:
            logger.error("Missing required environment variable: DISCORD_WEBHOOK_URL")
            return False
        if not DISCORD_WEBHOOK_URL.startswith('https://discord.com/api/webhooks/'):
            logger.error("DISCORD_WEBHOOK_URL appears invalid")
            return False
    else:
        logger.error("Invalid NOTIFY_SERVICE. Must be 'ntfy' or 'discord'")
        return False

    return True

def send_ntfy_notification(message: str, title: str = NOTIFY_SUBJECT) -> None:
    """Send a notification to ntfy."""
    headers = {
        "Title": title,
        "Content-Type": "text/plain; charset=utf-8"
    }
    if NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"

    try:
        response = requests.post(
            f"{NTFY_URL}/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"ntfy notification sent: {message}")
    except requests.RequestException as e:
        logger.error(f"Failed to send ntfy notification: {e}")

def send_discord_notification(message: str, title: str = NOTIFY_SUBJECT) -> None:
    """Send a notification to Discord via webhook."""
    payload = {
        "embeds": [{
            "title": title,
            "description": message,
            "color": 0x00ff00  # Green color
        }]
    }
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Discord notification sent: {message}")
    except requests.RequestException as e:
        logger.error(f"Failed to send Discord notification: {e}")

def send_notification(message: str, title: str = NOTIFY_SUBJECT) -> None:
    """Route notification to the appropriate service."""
    if NOTIFY_SERVICE == 'ntfy':
        send_ntfy_notification(message, title)
    elif NOTIFY_SERVICE == 'discord':
        send_discord_notification(message, title)

def follow_log(file_path: str) -> None:
    """Follow the log file, similar to tail -f."""
    file = Path(file_path)
    if not file.exists():
        logger.error(f"Log file {file_path} not found")
        return

    logger.info(f"Starting to monitor {file_path}")
    with open(file, "r", encoding='utf-8') as f:
        f.seek(0, 2)  # Seek to end
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
                
            # Check for join event
            if NOTIFY_JOIN:
                join_match = JOIN_PATTERN.search(line)
                if join_match:
                    player = join_match.group(1)
                    send_notification(f"{player} joined the server")
                    continue
                
            # Check for leave event
            if NOTIFY_LEAVE:
                leave_match = LEAVE_PATTERN.search(line)
                if leave_match:
                    player = leave_match.group(1)
                    send_notification(f"{player} left the server")
                    continue
                
            # Check for whitelist failure
            if NOTIFY_WHITELIST:
                whitelist_match = WHITELIST_PATTERN.search(line)
                if whitelist_match:
                    player = whitelist_match.group(1)
                    send_notification(f"{player} failed to join (not whitelisted)")
                    continue

def main() -> None:
    """Main function to start monitoring."""
    if not validate_config():
        logger.error("Configuration validation failed. Exiting...")
        exit(1)
    
    logger.info(
        f"Starting Minecraft server monitor "
        f"(Service: {NOTIFY_SERVICE}, Subject: {NOTIFY_SUBJECT}, "
        f"Join: {NOTIFY_JOIN}, Leave: {NOTIFY_LEAVE}, Whitelist: {NOTIFY_WHITELIST})"
    )
    try:
        follow_log(LOG_FILE)
    except KeyboardInterrupt:
        logger.info("Shutting down monitor")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
