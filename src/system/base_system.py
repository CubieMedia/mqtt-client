import abc
import logging
import time

from common import DEFAULT_MQTT_SERVER, DEFAULT_MQTT_USERNAME, DEFAULT_MQTT_PASSWORD, DEFAULT_LEARN_MODE
from common.mqtt_client_wrapper import CubieMediaMQTTClient
from common.python import get_configuration, set_configuration


class BaseSystem(abc.ABC):
    mqtt_client = None
    mqtt_server: str = DEFAULT_MQTT_SERVER
    mqtt_user: str = DEFAULT_MQTT_USERNAME
    mqtt_password: str = DEFAULT_MQTT_PASSWORD
    learn_mode: bool = DEFAULT_LEARN_MODE
    last_update = time.time()
    known_device_list: [] = []
    execution_mode = None

    def init(self, client_id: str):
        self.load()
        self.mqtt_client = CubieMediaMQTTClient(client_id)
        self.mqtt_client.connect(self)

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

    def load(self):
        logging.info("... loading config")

        common_config = get_configuration("common")
        device_list = get_configuration(self.execution_mode)

        self.mqtt_server = common_config['host'] if common_config else DEFAULT_MQTT_SERVER
        self.mqtt_user = common_config['username'] if common_config else DEFAULT_MQTT_USERNAME
        self.mqtt_password = common_config['password'] if common_config else DEFAULT_MQTT_PASSWORD
        self.learn_mode = common_config['learn-mode'] if common_config else DEFAULT_LEARN_MODE
        self.known_device_list = device_list if device_list else []

    def save(self, new_device=None):
        if new_device is None:
            set_configuration(self.execution_mode, self.known_device_list)

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
            logging.warning(f"... could not find device [{device}] to delete")

    def reset(self):
        self.known_device_list = []
        self.save()

    def set_learn_mode(self, enabled: bool):
        self.learn_mode = enabled
        self.save()

    def get_mqtt_data(self):
        return self.mqtt_server, self.mqtt_user, self.mqtt_password
