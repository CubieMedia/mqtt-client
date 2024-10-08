#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging

from paho.mqtt import client as mqtt

from common import CUBIE_ANNOUNCE, DEFAULT_TOPIC_COMMAND, CUBIE_RESET, QOS, CUBIE_RELOAD, \
    MQTT_CUBIEMEDIA


class CubieMediaMQTTClient:
    system = None

    def __init__(self, client_id):
        self.client_id = client_id
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id,
                                       clean_session=True,
                                       userdata=None, transport="tcp")

    def connect(self, system):
        self.system = system

        self.mqtt_client.username_pw_set(username=system.get_mqtt_login()[0],
                                         password=system.get_mqtt_login()[1])
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_message = self.on_message

        server = system.get_mqtt_server()
        logging.info(f"... connecting to MQTT-Service [{server}] as client [{self.client_id}]")
        self.mqtt_client.connect(server, 1883, 60)
        self.mqtt_client.loop_start()

    def disconnect(self):
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

    def publish(self, topic, payload: str, retain: bool = False):
        self.mqtt_client.publish(topic, payload, 0, retain)

    def subscribe(self, topic, qos):
        self.mqtt_client.subscribe(topic, qos)

    def on_message(self, client, userdata, msg):
        msg_payload = str(msg.payload.decode()).replace("False", "false").replace("True",
                                                                                  "true").strip()
        logging.debug(f"... ... mqtt message [{msg_payload}] on topic [{msg.topic}]")
        if msg_payload == CUBIE_ANNOUNCE:
            self.system.announce()
        elif msg_payload == CUBIE_RESET:
            self.system.reset()
        elif msg_payload == CUBIE_RELOAD:
            self.system.load()
        else:
            try:
                if msg.topic == DEFAULT_TOPIC_COMMAND:
                    message_data = json.loads(msg_payload)
                    if "type" in message_data and message_data["type"] == self.system.execution_mode:
                        if "mode" in message_data:
                            message_mode = message_data["mode"]
                            if message_mode == "update":
                                if "device" in message_data:
                                    new_device = message_data["device"]
                                    self.system.save(new_device)
                                else:
                                    logging.warning("WARNING: no device data given with update")
                            elif message_mode == "delete":
                                if "device" in message_data:
                                    new_device = message_data["device"]
                                    self.system.delete(new_device)
                                else:
                                    logging.warning(
                                        f"WARNING: no device data given [{message_data}] for deletion")
                            elif message_mode == 'values':
                                logging.info(f"... send data with [{msg.topic}]: {msg_payload}")
                                self.system.send(message_data)
                            else:
                                logging.warning(f"WARNING: unknown mode [{message_mode}]")
                        else:
                            logging.warning(
                                f"WARNING: no mode given, doing nothing on msg [{message_data}]")
                    else:
                        logging.debug(f"wrong or no type given, ignore message [{message_data}]")
                else:
                    if msg.topic.endswith("/command"):
                        topic_array = msg.topic.split("/")
                        if len(topic_array) > 3:
                            message_data = {'ip': topic_array[2].replace("_", "."),
                                            'id': topic_array[3],
                                            'state': msg_payload}
                            self.system.send(message_data)
                    else:
                        logging.warning(f"... ... unknown topic [{msg.topic}]")
            except json.JSONDecodeError as json_error:
                logging.warning(f"... could not decode message[{msg_payload}] with [{json_error}]")

    def on_connect(self, client, userdata, flags, rc):
        logging.info(
            f"... connected to Server [{self.system.get_mqtt_server()}] as client [{self.client_id}]")
        if rc == 0:
            logging.info(f"... ... subscribe to channel [{DEFAULT_TOPIC_COMMAND}]")
            self.mqtt_client.subscribe(DEFAULT_TOPIC_COMMAND, QOS)
            mode_specific_command_topic = f"{MQTT_CUBIEMEDIA}/{self.system.execution_mode}/command"
            logging.info(f"... ... subscribe to channel [{mode_specific_command_topic}]")
            self.mqtt_client.subscribe(mode_specific_command_topic, QOS)
            device_specific_command_topic = f"{MQTT_CUBIEMEDIA}/{self.system.execution_mode}/{self.system.string_ip}/command"
            logging.info(f"... ... subscribe to channel [{device_specific_command_topic}]")
            self.mqtt_client.subscribe(device_specific_command_topic, QOS)
            self.system.announce()
        else:
            logging.info("... bad connection please check login data")

    def on_disconnect(self, client, userdata, rc):
        if rc == 0:
            logging.info(
                f"... ...disconnected from Service [{self.system.get_mqtt_server}] with result [{rc}]")
        else:
            logging.warning(
                f"... ... lost connection to Service [{self.system.get_mqtt_server}] with result [{rc}]\n{userdata}")
