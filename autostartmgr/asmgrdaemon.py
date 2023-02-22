import subprocess
import threading
import socket
import atexit
import shlex
import toml
import json
import os

from . import DAEMON_PORT, SOCKET_DATA_LENGTH, __version__
from .paths import *
from .log import *

DEFAULT_ENTRY = {
    "Description": None,
    "service": {"ExecStartPre": None, "ExecStartPost": None},
    "exit": {"Restart": "never", "Attempts": None, "Timeout": 0.0, "ExecOnFail": None},
    "order": {"StartAfter": [], "StartBefore": []},
}

running_jobs = []


def merge_dicts(base, main):
    res = base.copy()
    for key in main:
        if type(key) == dict:
            res[key] = merge_dicts(base[key], main[key])
        else:
            res[key] = main[key]

    return res


def parse_entry(entry: dict):
    combined = merge_dicts(DEFAULT_ENTRY, entry)
    if "ExecStart" in combined["service"] and "Name" in combined:
        return "", combined
    return "service.ExecStart or Name missing", {}


def get_entries():
    results = []

    with open(ENTRY_STATUS_CONFIG_FILE, "r", encoding="UTF-8") as cfg:
        conf = json.load(cfg)
        enabled = conf["enabled"].copy()
        enabled_work = conf["enabled"].copy()

    for root, _, files in os.walk(ENTRY_FOLDER):
        for name in files:
            file = os.path.join(root, name)

            if not file.endswith(".toml"):
                continue

            error, entry = parse_entry(toml.load(file))
            res = {
                "file": file,
                "loaded": not bool(error),
                "status": error,
                "entry": entry,
                "enabled": False,
            }

            if not error:
                if entry["Name"] in enabled_work:
                    enabled_work.remove(entry["Name"])
                    res["enabled"] = True

            results.append(res)

    if len(enabled_work) > 0:
        for e in enabled_work:
            enabled.remove(e)

        with open(ENTRY_STATUS_CONFIG_FILE, "w", encoding="UTF-8") as cfg:
            conf["enabled"] = enabled
            cfg.write(json.dump(conf))

    return results


def handle_task(payload) -> str:
    payload = json.loads(payload.decode("UTF-8"))

    type = payload["type"]
    data = payload["data"]

    print(type, data)

    if type == "GET_ENTRIES":
        return json.dumps(get_entries())

    elif type == "START":
        for e in get_entries():
            if e["entry"]["Name"] == data["name"]:
                for j in running_jobs:
                    if j["entry"]["Name"] == data["name"]:
                        return json.dumps(
                            {
                                "error": True,
                                "message": f"Entry entry with name '{data['name']}' is already running.",
                            }
                        )

                run_entry(e["entry"])
                return json.dumps({"error": False})

        return json.dumps(
            {"error": True, "message": f"No entry with name '{data['name']}' found."}
        )

    elif type == "STOP":
        for j in running_jobs:
            if j["entry"]["Name"] == data["name"]:
                j["proc"].kill()
                return json.dumps({"error": False})

        return json.dumps(
            {"error": True, "message": f"No entry with name '{data['name']}' running."}
        )

    elif type == "ENABLE":
        with open(ENTRY_STATUS_CONFIG_FILE, "r+", encoding="UTF-8") as cfg:
            for e in get_entries():
                if e["entry"]["Name"] == data["name"]:
                    c = json.load(cfg)
                    if not data["name"] in c["enabled"]:
                        c["enabled"].append(data["name"])
                        cfg.seek(0)
                        json.dump(c, cfg)
                        return json.dumps({"error": False})
                    else:
                        return json.dumps(
                            {
                                "error": True,
                                "message": f"The entry with the name '{data['name']}' is already enabled.",
                            }
                        )
            return json.dumps(
                {
                    "error": True,
                    "message": f"No entry with name '{data['name']}' found.",
                }
            )

    elif type == "DISABLE":
        with open(ENTRY_STATUS_CONFIG_FILE, "r+", encoding="UTF-8") as cfg:
            c = json.load(cfg)
            for e in c["enabled"]:
                if e == data["name"]:
                    c["enabled"].remove(e)
                    cfg.seek(0)
                    cfg.truncate()
                    json.dump(c, cfg)
                    return json.dumps({"error": False})
        return json.dumps(
            {
                "error": True,
                "message": f"No entry with name '{data['name']}' is currently enabled.",
            }
        )

    elif type == "GET_VERSION":
        return {"version": __version__}

    else:
        return json.dumps(
            {
                "error": True,
                "message": f"This command is not supported by this version of the autostartmgr-daemon. Supported commands: GET_ENTRIES, START, STOP, ENABLE, DISABLE, GET_VERSION. This daemon is running on version {__version__}.",
            }
        )


def run_entry(entry: dict):
    global running_jobs

    print(entry)
    if entry["service"]["ExecStartPre"]:
        os.system(entry["service"]["ExecStartPre"])

    command_line = shlex.split(entry["service"]["ExecStart"])

    running_jobs.append(
        {
            "proc": subprocess.Popen(command_line),
            "cmd_line": command_line,
            "entry": entry,
            "times_restarted": 0,
            "waiting_for_restart": False,
        }
    )


def restart_job_after_timeout(job: dict):
    job["waiting_for_restart"] = True
    time.sleep(job["entry"]["exit"]["Timeout"])
    job["proc"] = subprocess.Popen(job["cmd_line"])
    job["waiting_for_restart"] = False
    job["times_restarted"] += 1


def exec_fail(job):
    if job["entry"]["exit"]["ExecOnFail"]:
        subprocess.Popen(shlex.split(job["entry"]["exit"]["ExecOnFail"]))


def manage_running():
    global running_jobs

    while True:
        for job in running_jobs:
            if job["proc"].poll() is not None:
                if job["waiting_for_restart"]:
                    continue

                if job["proc"].returncode == 0:
                    if job["entry"]["service"]["ExecStartPost"]:
                        subprocess.Popen(
                            shlex.split(job["entry"]["service"]["ExecStartPost"])
                        )
                    running_jobs.remove(job)
                    continue

                match job["entry"]["exit"]["Restart"]:
                    case "never", _:
                        exec_fail(job)
                        running_jobs.remove(job)
                    case "always":
                        threading.Thread(
                            target=restart_job_after_timeout, args=(job,)
                        ).start()
                    case "specific":
                        if job["times_restarted"] < job["entry"]["exit"]["Attempts"]:
                            threading.Thread(
                                target=restart_job_after_timeout, args=(job,)
                            ).start()
                        else:
                            exec_fail(job)
                            running_jobs.remove(job)


def start():
    os.environ["LOG_FILE"] = DAEMON_LOG_FILE

    if not os.path.isfile(ENTRY_STATUS_CONFIG_FILE):
        log(LOGPRESET_INFO, "Config not found, creating...")
        with open(ENTRY_STATUS_CONFIG_FILE, "w+", encoding="UTF-8") as cfg:
            json.dump({"enabled": []}, cfg)

    log(LOGPRESET_INFO, "Creating socket...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("localhost", DAEMON_PORT))
        s.listen(5)
    except Exception as e:
        log(LOGPRESET_ERROR, "Failed to create socket: " + str(e))
        exit(1)
    log(LOGPRESET_SUCCESS, "Created socket.")

    atexit.register(s.close)

    log(LOGPRESET_INFO, "Starting enabled entries...")

    enabled = [e["entry"] for e in get_entries() if e["enabled"]]

    for e in enabled:  # TODO: Starting order
        run_entry(e)

    log(LOGPRESET_SUCCESS, f"Started all {len(enabled)} enabled entries.")

    log(LOGPRESET_INFO, "Starting job monitoring...")

    th = threading.Thread(target=manage_running)
    th.daemon = True
    th.start()

    log(LOGPRESET_SUCCESS, "Daemon started successfully, ready for requests.")

    while True:
        try:
            conn, address = s.accept()
            data = conn.recv(SOCKET_DATA_LENGTH)
            if data:
                log(LOGPRESET_INFO, "Got request, starting handling...")
                try:
                    conn.send(handle_task(data).encode("UTF-8"))
                except Exception as e:
                    log(LOGPRESET_ERROR, "Failed to handle request: " + str(e))
                    continue
                log(LOGPRESET_SUCCESS, "Successfully handled request.")
        except KeyboardInterrupt:
            print("")
            log(LOGPRESET_ERROR, "Received KeyboardInterrupt, stopping...")
            exit(0)
