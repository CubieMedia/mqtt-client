import abc
import json
import logging
import time

from common import MQTT_CUBIEMEDIA, MQTT_HOMEASSISTANT_PREFIX
from common import TIMEOUT_UPDATE
from common.homeassistant import MQTT_BUTTON, PAYLOAD_BUTTON, MQTT_NAME, MQTT_AVAILABILITY_TOPIC, \
    MQTT_COMMAND_TOPIC, MQTT_UNIQUE_ID, \
    MQTT_DEVICE, MQTT_DEVICE_IDS
from common.mqtt_client_wrapper import CubieMediaMQTTClient
from common.network import get_ip_address
from common.python import get_configuration, set_configuration, get_mqtt_configuration, \
    system_reboot

SERVICES = {"reboot": {"name": "Reboot System"}}


class BaseSystem(abc.ABC):
    mqtt_client = None
    client_id = 'unknown'
    ip_address = None
    string_ip = 'unset'
    last_update = time.time() - TIMEOUT_UPDATE
    config: [] = []
    mqtt_config: [] = []
    execution_mode = "Base"

    def __init__(self):
        self.ip_address = get_ip_address()
        self.string_ip = self.ip_address.replace(".", "_")
        self.client_id = f"{self.ip_address}-{self.execution_mode}-client"
        self.mqtt_client = CubieMediaMQTTClient(self.client_id)

    def init(self):
        logging.info(f"... init base system [{self.client_id}]")
        self.load()
        self.mqtt_client.connect(self)

    def shutdown(self):
        logging.info(
            f"... disconnect mqtt client [{self.client_id}] from [{self.get_mqtt_server()}]")
        if self.mqtt_client:
            self.mqtt_client.disconnect()

    def action(self, device: {}) -> bool:
        raise NotImplementedError

    def update(self) -> {}:
        # Base system has no entities
        # no data is updated so there will be no actions executed
        data = {}

        return data

    def send(self, data: {}):
        if "id" in data and "state" in data:
            if data["id"] in SERVICES:
                logging.info("... ... reboot is [%s]", data['state'] == 'PRESS')
                system_reboot()
            else:
                logging.warning(
                    "unknown service in data while writing value to victron system [%s]" % data)
        else:
            logging.warning("missing id and/or state in data [%s] at base system" % data)

    def announce(self):
        for service, attributes in SERVICES.items():
            config_topic = f"{MQTT_HOMEASSISTANT_PREFIX}/{MQTT_BUTTON}/{self.string_ip}-{service}/config"
            state_topic = f"{MQTT_CUBIEMEDIA}/base/{self.string_ip}/{service}"
            unique_id = f"{self.string_ip}-base-{service}"
            availability_topic = f"{MQTT_CUBIEMEDIA}/base/{self.string_ip}/online"

            payload = PAYLOAD_BUTTON
            payload[MQTT_NAME] = attributes['name']
            payload[MQTT_COMMAND_TOPIC] = state_topic + "/command"
            payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
            payload[MQTT_UNIQUE_ID] = unique_id
            payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = self.string_ip
            payload[MQTT_DEVICE][MQTT_NAME] = f"CubieMedia Gateway ({self.ip_address})"

            self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)

    def set_availability(self, state: bool):
        self.mqtt_client.publish(
            f"{MQTT_CUBIEMEDIA}/base/{self.string_ip}/online",
            str(state).lower())

    def load(self):
        logging.info("... loading config")

        self.mqtt_config = get_mqtt_configuration()
        if self.execution_mode != "Base":
            self.config = get_configuration(self.execution_mode)

    def save(self, device=None):
        if device and 'client_id' not in device:
            device['client_id'] = self.client_id
        if device and 'id' in device:
            self.config = [device if device['id'] == temp_device['id'] else temp_device for
                           temp_device in self.config]
            if device not in self.config:
                self.config.append(device)
        if self.execution_mode != "Base":
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

    def get_mqtt_server(self):
        return self.mqtt_config['server']

    def get_mqtt_login(self):
        return (self.mqtt_config['username'],
                self.mqtt_config['password'])
