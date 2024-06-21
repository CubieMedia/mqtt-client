import abc
import json
import logging

from common import MQTT_CUBIEMEDIA, MQTT_HOMEASSISTANT_PREFIX, CUBIE_ENOCEAN, CUBIE_RELAY, QOS
from common.homeassistant import MQTT_BUTTON, PAYLOAD_BUTTON, MQTT_NAME, MQTT_AVAILABILITY_TOPIC, \
    MQTT_COMMAND_TOPIC, MQTT_UNIQUE_ID, \
    MQTT_DEVICE, MQTT_DEVICE_IDS, MQTT_DEVICE_DESCRIPTION
from common.mqtt_client_wrapper import CubieMediaMQTTClient
from common.network import get_ip_address
from common.python import get_configuration, set_configuration, get_mqtt_configuration, get_system_configuration, \
    execute_command

EXECUTION_MODE_BASE = "base"


def system_reboot(system):
    logging.info(f"... system reboot has been executed for [{system.ip_address}]")
    execute_command("sleep 3")


def system_reset(system):
    logging.info(f"... system reset has been executed for [{system.ip_address}]")
    system.reset()


SERVICES = {
    "reboot": {"name": "Reboot System", "action": system_reboot},
    "reset": {"name": "Reset Devices", "action": system_reset, "modes": [CUBIE_ENOCEAN, CUBIE_RELAY]}
}


class BaseSystem(abc.ABC):
    mqtt_client = None
    client_id = 'unknown'
    ip_address = None
    string_ip = 'unset'
    last_update = 0
    config: [] = []
    mqtt_config: {} = {}
    system_config: [] = []
    execution_mode = EXECUTION_MODE_BASE

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

    def send(self, data: {}) -> bool:
        if all(attribute in data for attribute in ['id', 'state']):
            data_id = data["id"]
            data_state = data["state"]
            if data_id in SERVICES:
                action = SERVICES[data_id]['action']
                action(self)
                return True
            else:
                logging.warning("unknown service in data while writing value to system [%s]", data)
        else:
            logging.warning("missing id and/or state in data [%s] at base system" % data)
        return False

    def announce(self):
        for service, attributes in SERVICES.items():
            if 'modes' not in attributes or self.execution_mode in attributes['modes']:
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
                payload[MQTT_DEVICE][MQTT_NAME] = f"MQTT - Gateway ({self.ip_address})"
                payload[MQTT_DEVICE][MQTT_DEVICE_DESCRIPTION] = f"Gateway ({self.ip_address})"

                self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)

                service_specific_command_topic = f"{MQTT_CUBIEMEDIA}/base/{self.string_ip}/{service}/command"
                logging.info(f"... ... subscribe to channel [{service_specific_command_topic}]")
                self.mqtt_client.subscribe(service_specific_command_topic, QOS)

    def set_availability(self, state: bool):
        self.mqtt_client.publish(
            f"{MQTT_CUBIEMEDIA}/base/{self.string_ip}/online",
            str(state).lower())

    def load(self):
        logging.info("... loading config")

        self.mqtt_config = get_mqtt_configuration()
        self.system_config = get_system_configuration()
        if self.execution_mode != "base":
            self.config = get_configuration(self.execution_mode)

    def save(self, device=None):
        if device and 'client_id' not in device:
            device['client_id'] = self.client_id
        if device and 'id' in device:
            self.config = [device if device['id'] == temp_device['id'] else temp_device for
                           temp_device in self.config]
            if device not in self.config:
                self.config.append(device)
        if self.execution_mode != EXECUTION_MODE_BASE:
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
