import logging
import subprocess
import time
from unittest.mock import MagicMock

import psutil

# if you use authentication on your local mosquitto server change this accordingly (Host,Username,Password)
AUTHENTICATION_MOCK = MagicMock(return_value=("localhost", None, None))


def check_mqtt_server():
    if "mosquitto" not in (p.name() for p in psutil.process_iter()):
        try:
            logging.info("no mqtt server found, starting mosquitto for testing")
            mqtt_server_process = subprocess.Popen("mosquitto")
            time.sleep(1)
            return mqtt_server_process
        except FileNotFoundError:
            logging.error("could not start mosquitto [sudo apt install mosquitto]")
    return None
