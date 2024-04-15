#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import copy
import json
import logging
import threading
import time
from json import JSONDecodeError

from paho.mqtt import client as mqtt

from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE, CUBIE_VICTRON, QOS, EXPORT_CORRECTION_FACTOR, \
    IMPORT_CORRECTION_FACTOR, COLOR_YELLOW, COLOR_DEFAULT
from system.base_system import BaseSystem

SERVICE_LIST = [
    "battery_power",
    "battery_soc",
    "battery_charged",
    "battery_discharged",
    "grid_exported",
    "grid_imported",
    "grid_lost_alarm",
    "allow_charge",
    "allow_discharge"
]
TOPIC_READ_LIST = [
    "system/0/Dc/Battery/Power",
    "system/0/Dc/Battery/Soc",
    "vebus/276/Energy/OutToInverter",
    "vebus/276/Energy/InverterToAcOut",
    "grid/30/Ac/Energy/Reverse",
    "grid/30/Ac/Energy/Forward",
    "vebus/276/Alarms/GridLost",
    "settings/0/Settings/SystemSetup/MaxChargeCurrent",
    "settings/0/Settings/CGwacs/MaxDischargePower"
]
VICTRON_WRITE_TOPIC = "W/c0619ab33552/settings/0/"


def get_service_from_topic(topic):
    return SERVICE_LIST[TOPIC_READ_LIST.index(topic)]


class VictronSystem(BaseSystem):
    victron_system = {}
    victron_mqtt_client = None
    export_correction_factor = 1
    import_correction_factor = 1
    updated_data = {"devices": []}
    keepalive_thread = threading.Thread()
    keepalive_thread_event = threading.Event()

    def __init__(self):
        self.execution_mode = CUBIE_VICTRON
        super().__init__()

    def action(self, device):
        logging.debug("... ... received device action [%s]" % device)
        for topic in device.keys():
            payload = device[topic]
            topic = topic.lower()
            if 'battery' in topic:
                pass
            elif topic == SERVICE_LIST[4]:
                payload = round(float(payload) * self.export_correction_factor, 2)
                logging.debug("exported payload [%s]" % payload)
            elif topic == SERVICE_LIST[5]:
                payload = round(float(payload) * self.import_correction_factor, 2)
                logging.debug("imported payload [%s]" % payload)
            elif topic == SERVICE_LIST[6]:
                pass
            elif topic == SERVICE_LIST[7]:
                payload = 0 if device[topic] < 1 else 1
            elif topic == SERVICE_LIST[8]:
                payload = 0 if device[topic] == 0 else 1
            else:
                logging.warning("no logic for topic [%s]" % topic)

            self.mqtt_client.publish(
                f"{CUBIEMEDIA}/{self.execution_mode}/{self.victron_system['id'].replace('.', '_')}/{topic}", payload,
                True)
        return True

    def send(self, data):
        logging.debug("... ... send data[%s] from HA" % data)
        # {'ip': '192.168.25.24', 'id': 'charge', 'state': b'1'}
        if "id" in data and "state" in data:
            service_value = True if data["state"].decode('UTF-8') == "1" else False
            if data["id"] == SERVICE_LIST[7]:
                logging.info("... ... charging is [%s]" % service_value)
                value = '{"value": %s}' % (80 if service_value else 0)
                self.victron_mqtt_client.publish(VICTRON_WRITE_TOPIC + TOPIC_READ_LIST[7], value)
            elif data["id"] == SERVICE_LIST[8]:
                logging.info("... ... feeding is [%s]" % service_value)
                value = '{"value": %s}' % (-1 if service_value else 0)
                self.victron_mqtt_client.publish(VICTRON_WRITE_TOPIC + TOPIC_READ_LIST[8], value)
            else:
                logging.warning("unknown service in data while writing value to victron system [%s]" % data)
        else:
            logging.warning("missing id and/or state in data [%s]" % data)

    def update(self):
        data = self.updated_data
        self.updated_data = {"devices": []}
        return data

    def init(self):
        super().init()

        self.victron_system['client_id'] = self.client_id
        self.victron_mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=self.client_id, clean_session=True, userdata=None,
                                               transport="tcp")
        # self.mqtt_client.username_pw_set(username=user, password=password)
        self.victron_mqtt_client.on_connect = self.on_victron_connect
        self.victron_mqtt_client.on_disconnect = self.on_victron_disconnect
        self.victron_mqtt_client.on_message = self.on_victron_message

        if EXPORT_CORRECTION_FACTOR in self.victron_system:
            self.export_correction_factor = self.victron_system[EXPORT_CORRECTION_FACTOR]
        if IMPORT_CORRECTION_FACTOR in self.victron_system:
            self.import_correction_factor = self.victron_system[IMPORT_CORRECTION_FACTOR]

        logging.info("... starting keepalive thread")
        self.keepalive_thread = threading.Thread(target=self._run)
        self.keepalive_thread.daemon = True
        self.keepalive_thread.start()

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        logging.info("... stopping scan thread...")
        if not self.keepalive_thread_event.is_set():
            self.keepalive_thread_event.set()
            if self.keepalive_thread.is_alive():
                self.keepalive_thread.join()

        super().shutdown()
        logging.info("... disconnect victron client...")
        if self.victron_mqtt_client and self.victron_mqtt_client.is_connected():
            self.victron_mqtt_client.disconnect()

    def announce(self):
        if self.victron_mqtt_client and self.victron_mqtt_client.is_connected():
            logging.info("... ... announce victron_system [%s]" % self.victron_system["id"])
            temp_victron_system = copy.copy(self.victron_system)
            temp_victron_system['state'] = SERVICE_LIST
            self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(temp_victron_system))

            device_command_topic = f"{CUBIEMEDIA}/{self.execution_mode}/{self.victron_system['id'].replace('.', '_')}/+/command"
            logging.info(f"... ... subscribing to [{device_command_topic}] for victron write commands")
            self.mqtt_client.subscribe(device_command_topic, 2)

            self.set_availability(True)
        else:
            self.set_availability(False)

    def load(self):
        super().load()
        self.victron_system = self.config[0]

    def _run(self):
        self.keepalive_thread_event = threading.Event()

        count = 0
        while not self.keepalive_thread_event.is_set():
            if count == 0:
                if not self.victron_mqtt_client.is_connected():
                    self.connect_victron_system()
                else:
                    self.victron_mqtt_client.publish(("R/%s/keepalive" % self.config[0]["serial"]),
                                                     json.dumps(TOPIC_READ_LIST))
                    self.set_availability(True)
                count = 30
            else:
                count -= 1
            time.sleep(1)

        return True

    def connect_victron_system(self):
        logging.info("... connecting to Victron System [%s] as client [%s]" % (self.victron_system["id"], self.client_id))

        try:
            self.victron_mqtt_client.connect(self.victron_system["id"], 1883, 60)
            self.victron_mqtt_client.loop_start()
        except (ConnectionError, TimeoutError, OSError):
            pass

    def on_victron_message(self, client, userdata, msg):
        message_topic = msg.topic
        message_payload = msg.payload.decode('UTF-8')
        for topic in TOPIC_READ_LIST:
            if topic in message_topic and 'value' in message_payload:
                try:
                    logging.info(f"... ... message [{message_payload}] on topic [{topic}]")
                    service = get_service_from_topic(topic)
                    value = json.loads(message_payload)['value']
                    self.updated_data["devices"].append({service: value})
                except JSONDecodeError:
                    logging.warning(
                        f"message on topic [{topic}] with value [{msg.payload}] seems not to be json format")
                break

    def on_victron_connect(self, client, userdata, flags, rc):
        logging.info(f"... connected to Victron System [{self.victron_system['id']}] with result [{rc}]")
        if rc == 0:
            if 'serial' in self.victron_system:
                for victron_topic in TOPIC_READ_LIST:
                    victron_topic = ("N/%s/" % self.victron_system["serial"]) + victron_topic
                    logging.info(f"... ... subscribe to topic [{victron_topic}]")
                    client.subscribe(victron_topic, QOS)

                self.ip_address = self.victron_system['id']
                self.announce()
            else:
                logging.warning("WARNING: could not find serial, will not subscribe to any topics")
        else:
            logging.error("ERROR: bad connection (please check login data)")

    def on_victron_disconnect(self, client, userdata, rc):
        if rc == 0:
            logging.info("... ...disconnected from Victron System [%s] with result [%s]" % (client._host, rc))
        else:
            logging.warning("... ... lost connection to Victron System [%s] with result [%s]" % (client._host, rc))

        self.set_availability(False)

    def set_availability(self, state: bool):
        if 'id' in self.victron_system:
            self.mqtt_client.publish(
                f"{CUBIEMEDIA}/{self.execution_mode}/{self.victron_system['id'].replace('.', '_')}/online",
                str(state).lower())
        else:
            logging.debug(
                f"{COLOR_YELLOW}WARNING: could not set availability on uninitialised victron system{COLOR_DEFAULT}")
