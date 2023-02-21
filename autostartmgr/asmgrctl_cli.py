from typer import Typer

from .log import *
from .paths import *
from .asmgrctl_socket import send

from rich import print

app = Typer()


@app.command(help="List all services.")
def list():
    entries = send("GET_ENTRIES", {})
    for e in entries:
        print("")
        if e["loaded"]:
            print(
                f"[bold]{e['entry']['Name']}[/bold] ({e['file'].replace(ENTRY_FOLDER, '')}) [#828282 i]{'not ' if not e['enabled'] else ''}enabled[/#828282 i]"
            )
            print(" \ufb0c [#828282]Desc: [/#828282]" + e["entry"]["Description"])
            print(
                " \ufb0c [#828282]Exec: [/#828282]" + e["entry"]["service"]["ExecStart"]
            )
        else:
            print(
                f"[{LOGPRESET_ERROR['color']}]Entry at {e['file']} not loaded: {e['status']}"
            )


@app.command(help="Enable an autostart entry.")
def enable(service_name: str):
    data = send("ENABLE", {"name": service_name})
    if data["error"]:
        log(LOGPRESET_ERROR, data["message"])
    else:
        log(LOGPRESET_SUCCESS, f"Service {service_name} enabled.")


@app.command(help="Disable an autostart entry.")
def disable(service_name: str):
    data = send("DISABLE", {"name": service_name})
    if data["error"]:
        log(LOGPRESET_ERROR, data["message"])
    else:
        log(LOGPRESET_SUCCESS, f"Service {service_name} disabled.")


@app.command(help="Start an autostart entry. The execution order will be ignored.")
def start(service_name: str):
    data = send("START", {"name": service_name})
    if data["error"]:
        log(LOGPRESET_ERROR, data["message"])
    else:
        log(LOGPRESET_SUCCESS, f"Service {service_name} started.")


@app.command(help="Stop an autostart entry.")
def stop(service_name: str):
    data = send("STOP", {"name": service_name})
    if data["error"]:
        log(LOGPRESET_ERROR, data["message"])
    else:
        log(LOGPRESET_SUCCESS, f"Service {service_name} stopped.")


@app.command(help="Show directories")
def directories():
    print("[bold]Log directory: [/bold]" + LOG_DIRECTORY)
    print("[bold]Entry directory: [/bold]" + ENTRY_FOLDER)


def run():
    os.environ["LOG_FILE"] = CLIENT_LOG_FILE
    app()
