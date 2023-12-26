import abc
import logging
import time

from common import DEFAULT_MQTT_SERVER, DEFAULT_MQTT_USERNAME, DEFAULT_MQTT_PASSWORD, DEFAULT_LEARN_MODE, CUBIE_CORE, \
    CUBIEMEDIA
from common.mqtt_client_wrapper import CubieMediaMQTTClient
from common.python import get_configuration, set_configuration


class BaseSystem(abc.ABC):
    mqtt_client = None
    client_id = 'unknown'
    ip_address = None
    mqtt_server: str = DEFAULT_MQTT_SERVER
    mqtt_user: str = DEFAULT_MQTT_USERNAME
    mqtt_password: str = DEFAULT_MQTT_PASSWORD
    learn_mode: bool = DEFAULT_LEARN_MODE
    last_update = time.time()
    known_device_list: [] = []
    execution_mode = None

    def init(self, ip_address: str):
        self.load()
        self.ip_address = ip_address
        self.client_id = client_id = ip_address + "-" + self.execution_mode + "-client"
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
        self.mqtt_client.publish(
            f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/online",
            str(state).lower())

    def load(self):
        logging.info("... loading config")

        core_config = get_configuration(CUBIE_CORE)
        device_list = get_configuration(self.execution_mode)

        self.mqtt_server = core_config['host'] if core_config else DEFAULT_MQTT_SERVER
        self.mqtt_user = core_config['username'] if core_config else DEFAULT_MQTT_USERNAME
        self.mqtt_password = core_config['password'] if core_config else DEFAULT_MQTT_PASSWORD
        self.learn_mode = core_config['learn_mode'] if core_config else DEFAULT_LEARN_MODE
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
        logging.info("... resetting device list")
        self.known_device_list = []
        self.save()

    def set_learn_mode(self, enabled: bool):
        logging.info(f"... setting learn mode [{enabled}]")
        self.learn_mode = enabled
        self.save()

    def get_mqtt_data(self):
        return self.mqtt_server, self.mqtt_user, self.mqtt_password
