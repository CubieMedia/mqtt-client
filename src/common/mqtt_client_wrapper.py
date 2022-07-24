#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging

from common import CUBIE_ANNOUNCE, DEFAULT_TOPIC_COMMAND, CUBIE_RESET, QOS
from common.network import get_ip_address  # noqa
from common.python import install_package

try:
    from paho.mqtt import client as mqtt
except (ModuleNotFoundError, RuntimeError) as e:
    install_package("paho-mqtt")
    from paho.mqtt import client as mqtt


class CubieMediaMQTTClient:
    system = None

    def __init__(self, client_id):
        self.client_id = client_id
        self.mqtt_client = mqtt.Client(client_id=client_id, clean_session=True, userdata=None, transport="tcp")

    def connect(self, system):
        self.system = system
        server, user, password = system.get_mqtt_data()
        logging.info("... connecting to MQTT-Service [%s] as client [%s]" % (server, self.client_id))
        self.mqtt_client.username_pw_set(username=user, password=password)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_message = self.on_message

        self.mqtt_client.connect(server, 1883, 60)
        self.mqtt_client.loop_start()

    def disconnect(self):
        self.mqtt_client.disconnect()

    def publish(self, topic, payload):
        self.mqtt_client.publish(topic, payload, 0, True)

    def subscribe(self, topic, qos):
        self.mqtt_client.subscribe(topic, qos)

    def on_message(self, client, userdata, msg):
        # print(msg.payload)
        if msg.payload.decode('UTF-8') == CUBIE_ANNOUNCE:
            try:
                logging.info("... search request: announcing devices")
                self.system.announce()
            except Exception as error:
                logging.error(error)
        elif msg.payload.decode('UTF-8') == CUBIE_RESET:
            logging.info("... reset request: clear device list")
            self.system.reset()
        else:
            # print("... received data: format to json[%s]" % msg.payload)
            try:
                if msg.topic == DEFAULT_TOPIC_COMMAND:
                    message_data = json.loads(msg.payload.decode())
                    if "mode" in message_data:
                        message_mode = message_data["mode"]
                        if message_mode == "update":
                            if "device" in message_data:
                                new_device = message_data["device"]
                                self.system.save(new_device)
                            elif "learn_mode" in message_data:
                                self.system.set_learn_mode(message_data['learn_mode'])
                            else:
                                logging.warning("WARNING: no data given [device]")
                        elif message_mode == "delete":
                            if "device" in message_data:
                                new_device = message_data["device"]
                                self.system.delete(new_device)
                            else:
                                logging.warning("WARNING: no data given [device]")
                        elif message_mode == 'values':
                            logging.info("... send data with [%s]: %s" % (msg.topic, str(msg.payload)))
                            self.system.send(message_data)
                        else:
                            logging.warning("WARNING: unknown mode [%s]" % message_mode)
                    else:
                        logging.warning("WARNING: no mode given, doing nothing")
                else:
                    if msg.topic.endswith("/command"):
                        topic_array = msg.topic.split("/")
                        if len(topic_array) > 3:
                            message_data = {'ip': topic_array[1].replace("_", "."), 'id': topic_array[2],
                                            'state': msg.payload}
                            self.system.send(message_data)
                    else:
                        logging.warning("... ... unknown topic [%s]" % msg.topic)
            except json.JSONDecodeError:
                logging.warning("... could not decode message[%s]" % msg.payload.decode())

    def on_connect(self, client, userdata, flags, rc):
        logging.info("... connected to Service [%s]" % client._host)
        if rc == 0:
            logging.info("... ... subscribe to channel [%s]" % DEFAULT_TOPIC_COMMAND)
            client.subscribe(DEFAULT_TOPIC_COMMAND, QOS)
            self.system.announce()
        else:
            logging.info("... bad connection please check login data")

    @staticmethod
    def on_disconnect(client, userdata, rc):
        if rc == 0:
            logging.info("... ...disconnected from Service [%s] with result [%s]" % (client._host, rc))
        else:
            logging.warning("... ... lost connection to Service [%s] with result [%s]" % (client._host, rc))
