from rich import print
import os

LOGPRESET_ERROR = {"color": "#ed3276", "symbol": "❌", "text": "ERR "}
LOGPRESET_INFO = {"color": "#d8f0e4", "symbol": "🕛", "text": "INFO"}
LOGPRESET_SUCCESS = {"color": "#32ed93", "symbol": "✅", "text": "SUCC"}


def log(preset: dict, data: str):
    print(f"{preset['symbol']} [{preset['color']}]{data}[/{preset['color']}]")
    with open(os.environ["LOG_FILE"], "a", encoding="UTF-8") as l:
        l.write(preset["text"] + " " + data + "\n")
