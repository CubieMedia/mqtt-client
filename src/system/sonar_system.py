#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging
import random
import time

from serial import Serial, SerialException

from common import COLOR_YELLOW, COLOR_DEFAULT, CUBIE_SONAR, SONAR_PORT, CUBIE_DEVICE, CUBIE_SERIAL, \
    CUBIE_TYPE, MQTT_HOMEASSISTANT_PREFIX
from common import MQTT_CUBIEMEDIA
from common.homeassistant import MQTT_NAME, MQTT_STATE_TOPIC, MQTT_AVAILABILITY_TOPIC, \
    MQTT_UNIT_OF_MEASUREMENT, \
    MQTT_STATE_CLASS, MQTT_UNIQUE_ID, MQTT_DEVICE, MQTT_DEVICE_IDS, MQTT_DEVICE_DESCRIPTION, \
    ATTR_MEASUREMENT, MQTT_SENSOR, MQTT_UNIT, MQTT_CONFIG_TOPIC, PAYLOAD_SENSOR
from common.python import get_configuration
from system.base_system import BaseSystem

DEFAULT_UPDATE_INTERVAL = 10
DEFAULT_OFFSET = 0
DEFAULT_TRIGGER_OFFSET = 5
DEFAULT_DISTANCE_OFFSET = 500
DEFAULT_MAXIMAL_DISTANCE = 8000

SERVICES = {
    "distance": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        MQTT_UNIT: "mm",
        MQTT_STATE_CLASS: ATTR_MEASUREMENT
    },
    "percent": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        MQTT_UNIT: "%",
        MQTT_STATE_CLASS: ATTR_MEASUREMENT
    }
}


class SonarSystem(BaseSystem):
    communicator = None
    distance = None
    update_interval = None
    offset = None
    offset_trigger = 5
    maximal_distance = DEFAULT_MAXIMAL_DISTANCE
    distance_offset = DEFAULT_DISTANCE_OFFSET

    def __init__(self):
        self.execution_mode = CUBIE_SONAR
        super().__init__()

    def init(self):
        super().init()
        self.update_interval = self.config[0]['update_interval'] if 'update_interval' in \
                                                                    self.config[
                                                                        0] else DEFAULT_UPDATE_INTERVAL
        self.offset = self.config[0]['offset'] if 'offset' in self.config[0] else DEFAULT_OFFSET
        self.offset_trigger = self.config[0][
            'trigger_offset'] if 'trigger_offset' in self.config[0] else DEFAULT_TRIGGER_OFFSET
        self.distance_offset = self.config[0][
            'offset_distance'] if 'offset_distance' in self.config[0] else DEFAULT_DISTANCE_OFFSET
        self.maximal_distance = self.config[0][
            'maximal_distance'] if 'maximal_distance' in self.config[
            0] else DEFAULT_MAXIMAL_DISTANCE

        serial_port = None
        try:
            default_serial_port = SONAR_PORT
            serial_json = get_configuration(CUBIE_SERIAL)[0]
            if serial_json[CUBIE_TYPE] == CUBIE_SERIAL and CUBIE_DEVICE in serial_json:
                default_serial_port = serial_json[CUBIE_DEVICE]
            serial_port = self.config[0][CUBIE_DEVICE] if CUBIE_DEVICE in self.config[
                0] else default_serial_port
            self.communicator = Serial(serial_port, 9600)
            self.communicator.flush()
        except SerialException:
            logging.warning(
                f"{COLOR_YELLOW}could not initialise serial communication [{serial_port}], running in development mode?{COLOR_DEFAULT}")

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        super().shutdown()

    def action(self, device: {}):
        logging.info("... ... action for [%s]" % device)
        self.mqtt_client.publish(
            f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{self.string_ip}/distance",
            json.dumps(device['value']), True)
        percent = round(
            (self.maximal_distance - (device['value'])) / (
                    self.maximal_distance - self.distance_offset) * 100)
        self.mqtt_client.publish(
            f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{self.string_ip}/percent",
            percent, True)
        self.set_availability(True)

    def update(self):
        data = {}

        device_list = []
        if self.last_update < time.time() - self.update_interval:
            self.last_update = time.time()

            if self.communicator:
                self.communicator.write(bytearray([0x01]))
                self.communicator.flush()

                if self.communicator.in_waiting > 0:
                    response = str(self.communicator.read(self.communicator.in_waiting))
                    if "Gap=" in response:
                        distance = int(
                            response[response.index("Gap=") + 4:response.index("mm")]) + self.offset

                        if not self.distance or abs(self.distance - distance) > self.offset_trigger:
                            if 200 <= distance - self.offset <= 8000:
                                self.distance = distance
                                device = {'id': self.ip_address, CUBIE_TYPE: CUBIE_SONAR,
                                          'value': self.distance}
                                device_list.append(device)
                            else:
                                logging.warning(
                                    f"Distance [{distance}] is out of range, object too close or cable disconnected")
                    else:
                        logging.warning(f"Could not find [Gap] in response[{response}]")
            else:
                logging.warning("no communicator found, creating random values")
                device = {'id': self.ip_address, CUBIE_TYPE: CUBIE_SONAR,
                          'value': random.randint(self.distance_offset, self.maximal_distance)}
                device_list.append(device)

        data['devices'] = device_list
        return data

    def announce(self):
        super().announce()
        for device in self.config:
            if 'id' not in device:
                already_exists = False
                for temp_device in self.config:
                    if 'id' in temp_device and temp_device['id'] == self.ip_address:
                        already_exists = True
                        break
                if not already_exists:
                    device['id'] = self.ip_address
                else:
                    logging.warning(
                        f'{COLOR_YELLOW}something ist wrong with your config (id matching){COLOR_DEFAULT}')
                    break
            device['client_id'] = self.client_id
            logging.info("... ... announce sonar device [%s]", device)

            string_id = self.string_ip
            device_name = f"Sonar Device ({self.ip_address})"

            availability_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/online"

            for service, attributes in SERVICES.items():
                state_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/{service}"
                service_name = f"{service.replace('_', ' ').title()}"
                unique_id = f"{string_id}-{self.execution_mode}-{service}"
                config_topic = f"{MQTT_HOMEASSISTANT_PREFIX}/{attributes[MQTT_CONFIG_TOPIC]}/{string_id}-{service}/config"

                payload = PAYLOAD_SENSOR
                payload[MQTT_NAME] = service_name
                payload[MQTT_STATE_TOPIC] = state_topic
                payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
                payload[MQTT_STATE_CLASS] = attributes[MQTT_STATE_CLASS]
                payload[MQTT_UNIT_OF_MEASUREMENT] = attributes[MQTT_UNIT]
                payload[MQTT_UNIQUE_ID] = unique_id
                payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = f"{self.execution_mode}-{self.string_ip}"
                payload[MQTT_DEVICE][MQTT_NAME] = device_name
                payload[MQTT_DEVICE][MQTT_DEVICE_DESCRIPTION] = f"via Gateway ({self.ip_address})"

                self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)

    def set_availability(self, state: bool):
        super().set_availability(state)
        logging.debug("... ... set availability [%s]", state)
        availability_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{self.string_ip}/online"
        self.mqtt_client.publish(availability_topic, str(state).lower())
