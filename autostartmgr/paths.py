from appdirs import AppDirs

import time
import os

directories = AppDirs("autostartmgr", "PaddeCraft")

CONFIG_DIRECTORY = directories.user_config_dir
LOG_DIRECTORY = directories.user_log_dir

ENTRY_STATUS_CONFIG_FILE = os.path.join(CONFIG_DIRECTORY, "entries.json")
ENTRY_FOLDER = os.path.join(CONFIG_DIRECTORY, "entries")

DAEMON_LOG_FILE = os.path.join(LOG_DIRECTORY, "daemon-" + str(time.time()) + ".log")
CLIENT_LOG_FILE = os.path.join(LOG_DIRECTORY, "client-" + str(time.time()) + ".log")

for dir in [CONFIG_DIRECTORY, LOG_DIRECTORY, ENTRY_FOLDER]:
    os.makedirs(dir, exist_ok=True)
