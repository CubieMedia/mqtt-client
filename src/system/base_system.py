import abc
import logging
import time
from random import randint

from common.mqtt_client_wrapper import CubieMediaMQTTClient
from common.network import get_ip_address
from common.python import get_configuration, set_configuration, get_core_configuration
from src.common import CUBIEMEDIA


class BaseSystem(abc.ABC):
    mqtt_client = None
    client_id = 'unknown'
    ip_address = None
    last_update = time.time()
    config: [] = []
    core_config: [] = []
    execution_mode = "Base"

    def __init__(self):
        self.ip_address = get_ip_address()
        self.client_id = f"{self.ip_address}-{self.execution_mode}-client-{str(randint(0, 9))}"
        self.mqtt_client = CubieMediaMQTTClient(self.client_id)

    def init(self):
        self.load()
        self.mqtt_client.connect(self)

    def shutdown(self):
        self.mqtt_client.disconnect()

    def action(self, device):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError()

    def send(self, data):
        raise NotImplementedError()

    def announce(self):
        raise NotImplementedError()

    def set_availability(self, state: bool):
        self.mqtt_client.publish(
            f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/online",
            str(state).lower())

    def load(self):
        logging.info("... loading config")

        self.core_config = get_core_configuration(self.ip_address)
        if self.execution_mode != "Base":
            self.config = get_configuration(self.execution_mode)

    def save(self, new_device=None):
        if new_device and 'id' in new_device:
            self.config = [new_device if device['id'] == new_device['id'] else device for device in
                           self.config]
            if new_device not in self.config:
                self.config.append(new_device)
        set_configuration(self.execution_mode, self.config)

    def delete(self, device):
        deleted = False
        for known_device in self.config:
            if str(device['id']).upper() == str(known_device['id']).upper():
                self.config.remove(known_device)
                self.save()
                deleted = True
                break

        if deleted:
            logging.info(f"... deleted device [{device}]")
        else:
            logging.warning(f"... could not find device [{device}] to delete")

    def reset(self):
        logging.info("... resetting device list")
        self.config = []
        self.save()

    def get_mqtt_data(self):
        return (self.core_config['host'],
                self.core_config['username'],
                self.core_config['password'])
