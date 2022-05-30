import abc
import json
import time
import logging

from common import DEFAULT_MQTT_SERVER, DEFAULT_MQTT_USERNAME, DEFAULT_MQTT_PASSWORD, DEFAULT_LEARN_MODE
from common.mqtt_client_wrapper import CubieMediaMQTTClient


class BaseSystem(abc.ABC):
    mqtt_client = None
    mqtt_server: str = DEFAULT_MQTT_SERVER
    mqtt_user: str = DEFAULT_MQTT_USERNAME
    mqtt_password: str = DEFAULT_MQTT_PASSWORD
    learn_mode: bool = DEFAULT_LEARN_MODE
    last_update = time.time()
    known_device_list: [] = []
    config_file_name = "./device_list.json"

    def init(self, client_id: str):
        self.mqtt_client = CubieMediaMQTTClient(client_id)
        self.mqtt_client.connect(self)
        self.load()

    def shutdown(self):
        raise NotImplementedError

    def action(self, device):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError()

    def send(self, data):
        raise NotImplementedError()

    def announce(self):
        raise NotImplementedError()

    def set_availability(self, state: bool):
        raise NotImplementedError()

    def save(self, new_device: None):
        raise NotImplemented()

    def load(self):
        try:
            logging.info("... loading config")
            with open(self.config_file_name) as json_file:
                config = json.load(json_file)
                self.mqtt_server = config['host']
                self.mqtt_user = config['username']
                self.mqtt_password = config['password']
                self.learn_mode = config['learn_mode']
                self.known_device_list = config['deviceList']
        except (IOError, ValueError):
            logging.error("... ... could not read file, creating default config...")
            self.save()
            self.load()

    def delete(self, device):
        deleted = False
        for known_device in self.known_device_list:
            if str(device['id']).upper() == str(known_device['id']).upper():
                self.known_device_list.remove(known_device)
                self.save()
                deleted = True
                break

        if deleted:
            logging.info(f"... deleted device [{device}]")
        else:
            logging.warning(f"... could find device [{device}] to delete")

    def reset(self):
        self.known_device_list = []
        self.save()

    def set_learn_mode(self, enabled: bool):
        self.learn_mode = enabled
        self.save()

    def get_mqtt_data(self):
        return self.mqtt_server, self.mqtt_user, self.mqtt_password
