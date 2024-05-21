#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import json
import logging
import threading
import time
from json import JSONDecodeError

from paho.mqtt import client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from common import MQTT_CUBIEMEDIA, CUBIE_VICTRON, QOS, EXPORT_CORRECTION_FACTOR, \
    IMPORT_CORRECTION_FACTOR, COLOR_YELLOW, COLOR_DEFAULT, MQTT_HOMEASSISTANT_PREFIX
from common.homeassistant import MQTT_NAME, MQTT_COMMAND_TOPIC, \
    MQTT_STATE_TOPIC, MQTT_AVAILABILITY_TOPIC, MQTT_UNIT_OF_MEASUREMENT, MQTT_STATE_CLASS, \
    MQTT_DEVICE_CLASS, MQTT_UNIQUE_ID, MQTT_DEVICE, MQTT_DEVICE_IDS, MQTT_DEVICE_DESCRIPTION, \
    MQTT_BINARY_SENSOR, PAYLOAD_ACTOR, MQTT_BATTERY, MQTT_POWER, \
    MQTT_MEASUREMENT, MQTT_ENERGY, MQTT_SENSOR, MQTT_SWITCH, \
    PAYLOAD_SPECIAL_SENSOR, MQTT_UNIT, MQTT_CONFIG_TOPIC, VICTRON_MQTT_TOPIC, MQTT_TOTAL_INCREASING
from system.base_system import BaseSystem


def _correct_value(payload, factor) -> float:
    return round(float(payload) * factor, 2)


SERVICES = {
    "battery_power": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        VICTRON_MQTT_TOPIC: "system/0/Dc/Battery/Power",
        MQTT_UNIT: "W",
        MQTT_STATE_CLASS: MQTT_MEASUREMENT,
        MQTT_DEVICE_CLASS: MQTT_POWER
    },
    "battery_soc": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        VICTRON_MQTT_TOPIC: "system/0/Dc/Battery/Soc",
        MQTT_UNIT: "%",
        MQTT_STATE_CLASS: MQTT_MEASUREMENT,
        MQTT_DEVICE_CLASS: MQTT_BATTERY
    },
    "battery_charged": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        VICTRON_MQTT_TOPIC: "vebus/276/Energy/OutToInverter",
        MQTT_UNIT: "kWh",
        MQTT_STATE_CLASS: MQTT_TOTAL_INCREASING,
        MQTT_DEVICE_CLASS: MQTT_ENERGY
    },
    "battery_discharged": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        VICTRON_MQTT_TOPIC: "vebus/276/Energy/InverterToAcOut",
        MQTT_UNIT: "kWh",
        MQTT_STATE_CLASS: MQTT_TOTAL_INCREASING,
        MQTT_DEVICE_CLASS: MQTT_ENERGY
    },
    "grid_exported": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        VICTRON_MQTT_TOPIC: "grid/30/Ac/Energy/Reverse",
        MQTT_UNIT: "kWh",
        MQTT_STATE_CLASS: MQTT_TOTAL_INCREASING,
        MQTT_DEVICE_CLASS: MQTT_ENERGY
    },
    "grid_imported": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        VICTRON_MQTT_TOPIC: "grid/30/Ac/Energy/Forward",
        MQTT_UNIT: "kWh",
        MQTT_STATE_CLASS: MQTT_TOTAL_INCREASING,
        MQTT_DEVICE_CLASS: MQTT_ENERGY
    },
    "grid_lost_alarm": {
        MQTT_CONFIG_TOPIC: MQTT_BINARY_SENSOR,
        VICTRON_MQTT_TOPIC: "vebus/276/Alarms/GridLost",
    },
    "allow_charge": {
        MQTT_CONFIG_TOPIC: MQTT_SWITCH,
        VICTRON_MQTT_TOPIC: "settings/0/Settings/SystemSetup/MaxChargeCurrent",
    },
    "allow_discharge": {
        MQTT_CONFIG_TOPIC: MQTT_SWITCH,
        VICTRON_MQTT_TOPIC: "settings/0/Settings/CGwacs/MaxDischargePower"
    }
}
VICTRON_WRITE_TOPIC = "W/{}/"


def service_from_topic(topic: str):
    for service, attributes in SERVICES.items():
        if str(attributes[VICTRON_MQTT_TOPIC]).lower() == topic.lower():
            return service

    logging.warning(f"could not find service for topic [{topic}]")
    return "not found"


def victron_mqtt_topics() -> list:
    victron_mqtt_list = []
    for service, attributes in SERVICES.items():
        victron_mqtt_list.append(attributes[VICTRON_MQTT_TOPIC])
    return victron_mqtt_list


class VictronSystem(BaseSystem):
    victron_system = {}
    victron_mqtt_client = None
    _export_correction_factor = 1
    _import_correction_factor = 1
    _updated_data = {"devices": []}
    _keepalive_thread = threading.Thread()
    _keepalive_thread_event = threading.Event()

    def __init__(self):
        self.execution_mode = CUBIE_VICTRON
        super().__init__()

    def action(self, device):
        logging.debug("... ... received device action [%s]" % device)
        for topic in device.keys():
            payload = device[topic]
            topic = topic.lower()

            if topic in SERVICES:
                if topic == 'grid_exported':
                    payload = round(float(payload) * self._export_correction_factor, 2)
                    logging.debug("... ... ... recalculated exported payload [%s]" % payload)
                elif topic == 'grid_imported':
                    payload = round(float(payload) * self._import_correction_factor, 2)
                    logging.debug("... ... ... recalculated imported payload [%s]" % payload)
                elif topic == 'allow_charge':
                    payload = 0 if device[topic] < 1 else 1
                elif topic == 'allow_discharge':
                    payload = 0 if device[topic] == 0 else 1
                else:
                    pass  # do nothing with payload

            self.mqtt_client.publish(
                f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/"
                f"{self.victron_system['id'].replace('.', '_')}/{topic}",
                payload, True)

    def send(self, data):
        logging.debug("... ... send data[%s] from HA" % data)
        # {'ip': '192.168.25.24', 'id': 'charge', 'state': b'1'}
        if "id" in data and "state" in data:
            service_value = True if data["state"] == "1" else False
            if data['id'] in SERVICES:
                service = data['id']
                if service == 'allow_discharge':
                    logging.info("... ... feeding is [%s]" % service_value)
                    value = '{"value": %s}' % (-1 if service_value else 0)
                elif service == 'allow_charge':
                    logging.info("... ... charging is [%s]" % service_value)
                    value = '{"value": %s}' % (80 if service_value else 0)
                else:
                    value = service_value
                self.victron_mqtt_client.publish(
                    VICTRON_WRITE_TOPIC.format(self.victron_system['serial']) + SERVICES[service][
                        VICTRON_MQTT_TOPIC], value)
                return True
            else:
                return super().send(data)
        else:
            logging.warning("missing id and/or state in data [%s]" % data)
        return False

    def update(self):
        data = self._updated_data
        self._updated_data = {"devices": []}
        return data

    def init(self):
        super().init()

        self.victron_system['client_id'] = self.client_id
        self.victron_mqtt_client = mqtt.Client(CallbackAPIVersion.VERSION1, clean_session=True,
                                               userdata=None, transport="tcp")
        # self.mqtt_client.username_pw_set(username=user, password=password)
        self.victron_mqtt_client.on_connect = self.on_victron_connect
        self.victron_mqtt_client.on_disconnect = self.on_victron_disconnect
        self.victron_mqtt_client.on_message = self.on_victron_message

        if EXPORT_CORRECTION_FACTOR in self.victron_system:
            self._export_correction_factor = self.victron_system[EXPORT_CORRECTION_FACTOR]
        if IMPORT_CORRECTION_FACTOR in self.victron_system:
            self._import_correction_factor = self.victron_system[IMPORT_CORRECTION_FACTOR]

        logging.info("... starting keepalive thread")
        self._keepalive_thread = threading.Thread(target=self._run)
        self._keepalive_thread.daemon = True
        self._keepalive_thread.start()

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        logging.info("... stopping scan thread...")
        if not self._keepalive_thread_event.is_set():
            self._keepalive_thread_event.set()
            if self._keepalive_thread.is_alive():
                self._keepalive_thread.join()

        super().shutdown()
        logging.info("... disconnect victron client...")
        if self.victron_mqtt_client and self.victron_mqtt_client.is_connected():
            self.victron_mqtt_client.disconnect()

    def announce(self):
        super().announce()
        string_id = self.victron_system['id'].replace('.', '_')
        device_name = f"Victron System ({self.victron_system['id']})"
        service_specific_command_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/+/command"
        logging.info(f"... ... subscribe to channel [{service_specific_command_topic}]")
        self.mqtt_client.subscribe(service_specific_command_topic, QOS)

        logging.info("... ... announce victron_system with all actors and sensors [%s]", self.victron_system)
        availability_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/online"

        for service, attributes in SERVICES.items():
            state_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/{service}"
            service_name = f"{service.replace('_', ' ').title()}"
            unique_id = f"{string_id}-{self.execution_mode}-{service}"
            config_topic = f"{MQTT_HOMEASSISTANT_PREFIX}/{attributes[MQTT_CONFIG_TOPIC]}/{string_id}-{service}/config"

            if attributes[MQTT_CONFIG_TOPIC] == MQTT_SENSOR:
                payload = PAYLOAD_SPECIAL_SENSOR
                payload[MQTT_UNIT_OF_MEASUREMENT] = attributes[MQTT_UNIT]
                payload[MQTT_STATE_CLASS] = attributes[MQTT_STATE_CLASS]
                payload[MQTT_DEVICE_CLASS] = attributes[MQTT_DEVICE_CLASS]
            else:
                payload = PAYLOAD_ACTOR
                payload[MQTT_COMMAND_TOPIC] = state_topic + "/command"

            payload[MQTT_NAME] = service_name
            payload[MQTT_STATE_TOPIC] = state_topic
            payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
            payload[MQTT_UNIQUE_ID] = unique_id
            payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = f"{self.execution_mode}-{self.string_ip}"
            payload[MQTT_DEVICE][MQTT_NAME] = device_name
            payload[MQTT_DEVICE][MQTT_DEVICE_DESCRIPTION] = f"via Gateway ({self.ip_address})"

            self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)
        self.set_availability(True)

    def load(self):
        super().load()
        self.victron_system = self.config[0]

    def _run(self):
        self._keepalive_thread_event = threading.Event()

        count = 0
        while not self._keepalive_thread_event.is_set():
            if count == 0:
                if not self.victron_mqtt_client.is_connected():
                    self.connect_victron_system()
                else:
                    self.victron_mqtt_client.publish(("R/%s/keepalive" % self.config[0]["serial"]),
                                                     json.dumps(victron_mqtt_topics()))
                    count = 30
                self.set_availability(True)
            else:
                count -= 1
            time.sleep(1)

        return True

    def connect_victron_system(self):
        logging.info(
            "... connecting to Victron System [%s] as client [%s]" % (
                self.victron_system["id"], self.client_id))

        try:
            self.victron_mqtt_client.connect(self.victron_system["id"], 1883, 60)
            self.victron_mqtt_client.loop_start()
        except (ConnectionError, TimeoutError, OSError):
            pass

    def on_victron_message(self, client, userdata, msg):
        message_topic = msg.topic
        message_payload = msg.payload.decode('UTF-8')
        for topic in victron_mqtt_topics():
            if topic in message_topic and 'value' in message_payload:
                try:
                    logging.info(f"... ... message [{message_payload}] on topic [{topic}]")
                    service = service_from_topic(topic)
                    value = json.loads(message_payload)['value']
                    self._updated_data["devices"].append({service: value})
                except JSONDecodeError:
                    logging.warning(
                        f"message on topic [{topic}] with value [{msg.payload}] seems not to be json format")
                break

    def on_victron_connect(self, client, userdata, flags, rc):
        logging.info(
            f"... connected to Victron System [{self.victron_system['id']}] with result [{rc}]")
        if rc == 0:
            if 'serial' in self.victron_system:
                for service, attributes in SERVICES.items():
                    victron_topic = ("N/%s/" % self.victron_system["serial"]) + attributes[
                        VICTRON_MQTT_TOPIC]
                    logging.info(f"... ... subscribe to topic [{victron_topic}]")
                    client.subscribe(victron_topic, QOS)

                self.set_availability(True)
            else:
                logging.warning("WARNING: could not find serial, will not subscribe to any topics")
        else:
            logging.error("ERROR: bad connection (please check login data)")

    def on_victron_disconnect(self, client, userdata, rc):
        if rc == 0:
            logging.info("... ...disconnected from Victron System [%s] with result [%s]" % (
                client._host, rc))
        else:
            logging.warning("... ... lost connection to Victron System [%s] with result [%s]" % (
                client._host, rc))

        self.set_availability(False)

    def set_availability(self, state: bool):
        super().set_availability(state)
        if 'id' in self.victron_system:
            logging.debug("... ... set availability [%s]", state)
            self.mqtt_client.publish(
                f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{self.victron_system['id'].replace('.', '_')}/online",
                str(state).lower())
        else:
            logging.debug(
                f"{COLOR_YELLOW}WARNING: could not set availability on uninitialised victron system{COLOR_DEFAULT}")
