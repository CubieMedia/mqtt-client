#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import logging
import threading
import time
from json import JSONDecodeError

from paho.mqtt import client as mqtt

from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE, CUBIE_VICTRON, QOS
from system.base_system import BaseSystem

EXPORT_CORRECTION_FACTOR = 5

IMPORT_CORRECTION_FACTOR = 1.2


class VictronSystem(BaseSystem):
    topic_read_list = ["system/0/Dc/Battery/Power", "system/0/Dc/Battery/Soc",
                       "vebus/276/Energy/OutToInverter",
                       "vebus/276/Energy/InverterToAcOut",
                       "grid/30/Ac/Energy/Reverse",
                       "grid/30/Ac/Energy/Forward",
                       "vebus/276/Alarms/GridLost",
                       "settings/0/Settings/SystemSetup/MaxChargeCurrent",
                       "settings/0/Settings/CGwacs/MaxDischargePower"]
    service_list = ["battery_power", "battery_soc", "battery_charged", "battery_discharged",
                    "grid_exported", "grid_imported", "grid_lost_alarm",
                    "allow_charge", "allow_discharge"]
    victron_system = {}
    victron_mqtt_client = None
    updated_data = {"devices": []}
    keepalive_thread = threading.Thread()
    keepalive_thread_event = threading.Event()

    def __init__(self):
        super().__init__()
        self.execution_mode = CUBIE_VICTRON

    def action(self, device):
        logging.debug("... ... received device action [%s]" % device)
        for topic in device.keys():
            payload = device[topic]
            if 'battery' in topic:
                pass
            elif topic is self.service_list[4]:
                payload = round(float(payload) / EXPORT_CORRECTION_FACTOR, 2)
                logging.debug("exported payload [%s]" % payload)
                pass
            elif topic is self.service_list[5]:
                payload = round(float(payload) / IMPORT_CORRECTION_FACTOR, 2)
                logging.debug("imported payload [%s]" % payload)
                pass
            elif topic is self.service_list[6]:
                pass
            elif topic == self.service_list[7]:
                payload = 0 if device[topic] < 1 else 1
            elif topic == self.service_list[8]:
                payload = 0 if device[topic] == 0 else 1
            else:
                logging.warning("no logic for topic [%s]" % topic)

            self.mqtt_client.publish(
                f"{CUBIEMEDIA}/{self.execution_mode}/{self.victron_system['id'].replace('.', '_')}/{topic}", payload)
        return True

    def send(self, data):
        logging.debug("... ... send data[%s] from HA" % data)
        # {'ip': '192.168.25.24', 'id': 'charge', 'state': b'1'}
        if "id" in data and "state" in data:
            service_value = True if data["state"].decode('UTF-8') == "1" else False
            if data["id"] == self.service_list[7]:
                logging.info("... ... charging is [%s]" % service_value)
                value = '{"value": %s}' % (80 if service_value else 0)
                self.victron_mqtt_client.publish("W/c0619ab33552/settings/0/Settings/SystemSetup/MaxChargeCurrent",
                                                 value)
            elif data["id"] == self.service_list[8]:
                logging.info("... ... feeding is [%s]" % service_value)
                value = '{"value": %s}' % (-1 if service_value else 0)
                self.victron_mqtt_client.publish("W/c0619ab33552/settings/0/Settings/CGwacs/MaxDischargePower", value)
            else:
                logging.warning("unknown service in data while writing value to victron system [%s]" % data)
        else:
            logging.warning("missing id and/or state in data [%s]" % data)

    def update(self):
        data = self.updated_data
        self.updated_data = {"devices": []}
        return data

    def init(self, ip_address):
        super().init(ip_address)
        self.victron_mqtt_client = mqtt.Client(client_id=self.client_id, clean_session=True, userdata=None,
                                               transport="tcp")
        # self.mqtt_client.username_pw_set(username=user, password=password)
        self.victron_mqtt_client.on_connect = self.on_victron_connect
        self.victron_mqtt_client.on_disconnect = self.on_victron_disconnect
        self.victron_mqtt_client.on_message = self.on_victron_message

        logging.info("... ... starting keepalive thread")
        self.keepalive_thread = threading.Thread(target=self._run)
        self.keepalive_thread.daemon = True
        self.keepalive_thread.start()

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        logging.info("... stopping scan thread...")
        if not self.keepalive_thread_event.is_set():
            self.keepalive_thread_event.set()
            self.keepalive_thread.join()

    def announce(self):
        logging.info("... ... announce victron_system [%s]" % self.victron_system["id"])
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(self.victron_system))
        device_command_topic = f"{CUBIEMEDIA}/{self.execution_mode}/{self.victron_system['id'].replace('.', '_')}/+/command"
        logging.info(f"... ... subscribing to [{device_command_topic}] for victron write commands")
        self.mqtt_client.subscribe(device_command_topic, 2)
        self.set_availability(True)

    def save(self, new_device=None):
        super().save(new_device)

    def load(self):
        super().load()
        if len(self.known_device_list) == 0:
            self.known_device_list = [{"id": "192.168.25.24", "serial": "c0619ab33552", "type": CUBIE_VICTRON,
                                       "client_id": self.client_id}]
        self.victron_system = self.known_device_list[0]

    def _run(self):
        self.keepalive_thread_event = threading.Event()

        count = 0
        while not self.keepalive_thread_event.is_set():
            if count == 0:
                if not self.victron_mqtt_client.is_connected():
                    self.connect_victron_system(self.client_id)
                else:
                    self.victron_mqtt_client.publish(("R/%s/keepalive" % self.known_device_list[0]["serial"]),
                                                     json.dumps(self.topic_read_list))
                count = 3
            else:
                count -= 1
            time.sleep(1)

        return True

    def connect_victron_system(self, client_id):
        logging.info("... connecting to Victron System [%s] as client [%s]" % (self.victron_system["id"], client_id))

        try:
            self.victron_mqtt_client.connect(self.victron_system["id"], 1883, 60)
            self.victron_mqtt_client.loop_start()
        except ConnectionError:
            pass

    def on_victron_message(self, client, userdata, msg):
        for topic in self.topic_read_list:
            if topic in msg.topic:
                try:
                    logging.debug("... ... message on topic [%s] with value [%s]" % (topic, msg.payload))
                    service = self.get_service_from_topic(topic)
                    value = json.loads(msg.payload.decode('UTF-8'))['value']
                    self.updated_data["devices"].append({service: value})
                except JSONDecodeError:
                    logging.warning(
                        "message on topic [%s] with value [%s] seems not to be json format" % (topic, msg.payload))

    def on_victron_connect(self, client, userdata, flags, rc):
        logging.info("... connected to Victron System [%s] with result [%s]" % (client._host, rc))
        if rc == 0:
            for topic in self.topic_read_list:
                topic = ("N/%s/" % self.known_device_list[0]["serial"]) + topic
                logging.info("... ... subscribe to topic [%s]" % topic)
                client.subscribe(topic, QOS)

            self.set_availability(True)
        else:
            logging.info("... bad connection please check login data")

    def on_victron_disconnect(self, client, userdata, rc):
        if rc == 0:
            logging.info("... ...disconnected from Victron System [%s] with result [%s]" % (client._host, rc))
        else:
            logging.warning("... ... lost connection to Victron System [%s] with result [%s]" % (client._host, rc))

        self.set_availability(False)

    def set_availability(self, state: bool):
        self.mqtt_client.publish(
            f"{CUBIEMEDIA}/{self.execution_mode}/{self.victron_system['id'].replace('.', '_')}/online",
            str(state).lower())

    def get_service_from_topic(self, topic):
        return self.service_list[self.topic_read_list.index(topic)]
