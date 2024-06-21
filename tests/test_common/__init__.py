import logging
import subprocess
import time
from unittest.mock import MagicMock

import psutil

from common import DEFAULT_MQTT_SERVER, DEFAULT_MQTT_USERNAME, DEFAULT_MQTT_PASSWORD

# if you use authentication on your local mosquitto server change this accordingly
MQTT_HOST_MOCK = MagicMock(return_value=DEFAULT_MQTT_SERVER)
MQTT_LOGIN_MOCK = MagicMock(return_value=(DEFAULT_MQTT_USERNAME, DEFAULT_MQTT_PASSWORD))


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
