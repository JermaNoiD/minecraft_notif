import re
import time
import requests
import os
import logging
import stat
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
LOG_FORMAT = os.getenv('LOG_FORMAT', 'server').lower()  # 'server' or 'velocity'
NTFY_TOPIC = os.getenv('NTFY_TOPIC')
NTFY_URL = os.getenv('NTFY_URL', 'https://ntfy.sh')
NTFY_TOKEN = os.getenv('NTFY_TOKEN')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
NOTIFY_SUBJECT = os.getenv('NOTIFY_SUBJECT', 'Minecraft Server')  # Title for notifications
NOTIFY_JOIN = os.getenv('NOTIFY_JOIN', 'true').lower() == 'true'
NOTIFY_LEAVE = os.getenv('NOTIFY_LEAVE', 'true').lower() == 'true'
NOTIFY_WHITELIST = os.getenv('NOTIFY_WHITELIST', 'true').lower() == 'true'

# Regex patterns for events
# Standard Minecraft patterns
SERVER_JOIN_PATTERN = re.compile(r"\[Server thread/INFO\]: (\w+) joined the game")
SERVER_LEAVE_PATTERN = re.compile(r"\[Server thread/INFO\]: (\w+) left the game")
SERVER_WHITELIST_PATTERN = re.compile(r"\[Server thread/INFO\]: (\w+) was kicked due to: You are not white-listed on this server!")
# Velocity patterns
VELOCITY_JOIN_PATTERN = re.compile(r"\[server connection\] (\.?\w+) -> (\w+) has connected")
VELOCITY_LEAVE_PATTERN = re.compile(r"\[server connection\] (\.?\w+) -> (\w+) has disconnected")
VELOCITY_WHITELIST_PATTERN = re.compile(
    r"\[connected player\] (\.?\w+) \(/[\d.:]+\): disconnected while connecting to (\w+): You are not whitelisted on this server!"
)

def validate_config() -> bool:
    """Validate required environment variables based on notification service and log format."""
    if not LOG_FILE:
        logger.error("Missing required environment variable: LOG_FILE")
        return False
    
    if not Path(LOG_FILE).parent.exists():
        logger.error(f"Log file directory does not exist: {Path(LOG_FILE).parent}")
        return False

    if not NOTIFY_SUBJECT:
        logger.error("NOTIFY_SUBJECT cannot be empty")
        return False

    if LOG_FORMAT not in ('server', 'velocity'):
        logger.error("Invalid LOG_FORMAT. Must be 'server' or 'velocity'")
        return False

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

def get_file_info(file_path: str) -> Optional[dict]:
    """Get inode and modification time of a file, or None if it doesn't exist."""
    try:
        stat_info = os.stat(file_path)
        return {
            "inode": stat_info.st_ino,
            "mtime": stat_info.st_mtime
        }
    except (FileNotFoundError, PermissionError):
        return None

def get_latest_log_file(log_dir: Path) -> Optional[Path]:
    """Find the most recently modified log file in the directory."""
    try:
        log_files = [f for f in log_dir.iterdir() if f.is_file() and f.name.startswith('latest.log')]
        if not log_files:
            return None
        return max(log_files, key=lambda f: os.stat(f).st_mtime)
    except (OSError, PermissionError) as e:
        logger.error(f"Error scanning log directory {log_dir}: {e}")
        return None

def follow_log(file_path: str) -> None:
    """Follow the log file, handling rotations by scanning the log directory."""
    file = Path(file_path)
    log_dir = file.parent
    current_inode = None
    current_mtime = None
    file_handle = None
    last_check = 0
    check_interval = 5  # Check for file changes every 5 seconds

    # Select patterns based on LOG_FORMAT
    join_pattern = VELOCITY_JOIN_PATTERN if LOG_FORMAT == 'velocity' else SERVER_JOIN_PATTERN
    leave_pattern = VELOCITY_LEAVE_PATTERN if LOG_FORMAT == 'velocity' else SERVER_LEAVE_PATTERN
    whitelist_pattern = VELOCITY_WHITELIST_PATTERN if LOG_FORMAT == 'velocity' else SERVER_WHITELIST_PATTERN

    logger.info(f"Starting to monitor {file_path} in directory {log_dir} with log format: {LOG_FORMAT}")

    while True:
        try:
            # Periodically check for log file changes
            current_time = time.time()
            if current_time - last_check >= check_interval:
                # Find the latest log file
                latest_log = get_latest_log_file(log_dir)
                file_exists = file.exists()

                # If no log file exists, wait and retry
                if not file_exists or not latest_log:
                    if file_handle:
                        file_handle.close()
                        file_handle = None
                        logger.warning(f"Log file {file_path} not found, waiting for it to appear")
                    time.sleep(1)
                    continue

                # Get current file info
                file_info = get_file_info(file_path)
                if file_info:
                    new_inode = file_info["inode"]
                    new_mtime = file_info["mtime"]
                else:
                    new_inode = None
                    new_mtime = None

                # Check if the file has changed (inode or mtime indicates rotation)
                if (new_inode != current_inode or new_mtime != current_mtime or file_handle is None) and file_info:
                    if file_handle:
                        file_handle.close()
                        logger.info(
                            f"Log file changed (inode: {current_inode} -> {new_inode}, "
                            f"mtime: {current_mtime} -> {new_mtime}), reopening {file_path}"
                        )
                    file_handle = open(file, "r", encoding='utf-8')
                    file_handle.seek(0, 2)  # Seek to end
                    current_inode = new_inode
                    current_mtime = new_mtime
                    logger.info(f"Monitoring log file {file_path} (inode: {current_inode}, mtime: {current_mtime})")

                last_check = current_time

            # Read new lines
            if file_handle:
                line = file_handle.readline()
                if not line:
                    time.sleep(0.1)  # Avoid CPU overuse
                    continue

                # Check for join event
                if NOTIFY_JOIN:
                    join_match = join_pattern.search(line)
                    if join_match:
                        player = join_match.group(1)
                        if LOG_FORMAT == 'velocity':
                            server = join_match.group(2)
                            message = f"{player} joined {server}"
                        else:
                            message = f"{player} joined the server"
                        send_notification(message)
                        continue
                
                # Check for leave event
                if NOTIFY_LEAVE:
                    leave_match = leave_pattern.search(line)
                    if leave_match:
                        player = leave_match.group(1)
                        if LOG_FORMAT == 'velocity':
                            server = leave_match.group(2)
                            message = f"{player} left {server}"
                        else:
                            message = f"{player} left the server"
                        send_notification(message)
                        continue
                
                # Check for whitelist failure
                if NOTIFY_WHITELIST:
                    whitelist_match = whitelist_pattern.search(line)
                    if whitelist_match:
                        player = whitelist_match.group(1)
                        if LOG_FORMAT == 'velocity':
                            server = whitelist_match.group(2)
                            message = f"{player} failed to join {server} (not whitelisted)"
                        else:
                            message = f"{player} failed to join (not whitelisted)"
                        send_notification(message)
                        continue

        except (IOError, PermissionError) as e:
            logger.error(f"Error reading log file: {e}")
            if file_handle:
                file_handle.close()
                file_handle = None
            time.sleep(1)  # Wait before retrying
        except Exception as e:
            logger.error(f"Unexpected error in follow_log: {e}")
            time.sleep(1)

def main() -> None:
    """Main function to start monitoring."""
    if not validate_config():
        logger.error("Configuration validation failed. Exiting...")
        exit(1)
    
    logger.info(
        f"Starting Minecraft server monitor "
        f"(Service: {NOTIFY_SERVICE}, Log Format: {LOG_FORMAT}, Subject: {NOTIFY_SUBJECT}, "
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
