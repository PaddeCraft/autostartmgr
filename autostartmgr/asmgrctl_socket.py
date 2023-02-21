import socket
import json


from . import DAEMON_PORT, SOCKET_DATA_LENGTH
from .log import *


def send(type, data):
    log(LOGPRESET_INFO, "Connection to daemon...")

    try:
        s = socket.socket()
        s.connect(("localhost", DAEMON_PORT))
    except ConnectionRefusedError:
        log(LOGPRESET_ERROR, "Could not connect to daemon.")
        exit(1)

    log(LOGPRESET_SUCCESS, "Connected to daemon.")
    log(LOGPRESET_INFO, "Sending data to daemon...")

    payload = {"type": type, "data": data}
    s.send(json.dumps(payload).encode("UTF-8"))

    log(LOGPRESET_INFO, "Waiting for response...")

    data = json.loads(s.recv(SOCKET_DATA_LENGTH).decode("UTF-8"))

    log(LOGPRESET_SUCCESS, "Received data from daemon.")
    log(LOGPRESET_INFO, "Closing connection to daemon...")

    s.close()

    log(LOGPRESET_SUCCESS, "Transmission succeeded.")

    return data
