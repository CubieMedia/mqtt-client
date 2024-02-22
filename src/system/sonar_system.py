#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging
import time

from serial import Serial, SerialException

from common import COLOR_YELLOW, COLOR_DEFAULT, CUBIE_SONAR, SONAR_PORT, CUBIE_DEVICE, CUBIE_SERIAL, \
    CUBIE_TYPE
from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE
from common.python import get_configuration
from system.base_system import BaseSystem

DEFAULT_UPDATE_INTERVAL = 10
DEFAULT_OFFSET = 0
DEFAULT_TRIGGER_OFFSET = 5
DEFAULT_DISTANCE_OFFSET = 500
DEFAULT_MAXIMAL_DISTANCE = 8000


class SonarSystem(BaseSystem):
    communicator = None
    distance = None
    update_interval = None
    offset = None
    offset_trigger = 5
    maximal_distance = 8000
    offset_distance = 500

    def __init__(self):
        self.execution_mode = CUBIE_SONAR
        super().__init__()

    def init(self):
        super().init()
        self.update_interval = self.config[0]['update_interval'] if 'update_interval' in self.config[
            0] else DEFAULT_UPDATE_INTERVAL
        self.offset = self.config[0]['offset'] if 'offset' in self.config[0] else DEFAULT_OFFSET
        self.offset_trigger = self.config[0][
            'trigger_offset'] if 'trigger_offset' in self.config[0] else DEFAULT_TRIGGER_OFFSET
        self.offset_distance = self.config[0][
            'offset_distance'] if 'offset_distance' in self.config[0] else DEFAULT_DISTANCE_OFFSET
        self.maximal_distance = self.config[0][
            'maximal_distance'] if 'maximal_distance' in self.config[0] else DEFAULT_MAXIMAL_DISTANCE

        serial_port = None
        try:
            default_serial_port = SONAR_PORT
            serial_json = get_configuration(CUBIE_SERIAL)[0]
            if serial_json[CUBIE_TYPE] == CUBIE_SERIAL and CUBIE_DEVICE in serial_json:
                default_serial_port = serial_json[CUBIE_DEVICE]
            serial_port = self.config[0][CUBIE_DEVICE] if CUBIE_DEVICE in self.config[0] else default_serial_port
            self.communicator = Serial(serial_port, 9600)
            self.communicator.flush()
        except SerialException:
            logging.warning(
                f"{COLOR_YELLOW}could not initialise serial communication [{serial_port}], running in development mode?{COLOR_DEFAULT}")

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        super().shutdown()

    def action(self, device):
        logging.info("... ... action for [%s]" % device)
        self.mqtt_client.publish(f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/distance",
                                 json.dumps(device['value']), True)
        percent = round(
            (self.maximal_distance - (device['value'])) / (self.maximal_distance - self.offset_distance) * 100)
        self.mqtt_client.publish(f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/percent",
                                 percent, True)

    def update(self):
        data = {}

        device_list = []
        if self.last_update < time.time() - self.update_interval:
            self.set_availability(True)
            self.last_update = time.time()

            if self.communicator:
                self.communicator.write(bytearray([0x01]))
                self.communicator.flush()

                if self.communicator.in_waiting > 0:
                    response = str(self.communicator.read(self.communicator.in_waiting))
                    if "Gap=" in response:
                        distance = int(response[response.index("Gap=") + 4:response.index("mm")]) + self.offset

                        if not self.distance or abs(self.distance - distance) > self.offset_trigger:
                            if 200 <= distance - self.offset <= 8000:
                                self.distance = distance
                                device = {'id': self.ip_address, CUBIE_TYPE: CUBIE_SONAR, 'value': self.distance}
                                device_list.append(device)
                            else:
                                logging.warning(
                                    f"Distance [{distance}] is out of range, object too close or cable disconnected")
                    else:
                        logging.warning(f"Could not find [Gap] in response[{response}]")

        data['devices'] = device_list
        return data

    def announce(self):
        device = {'id': self.ip_address, CUBIE_TYPE: CUBIE_SONAR, 'client_id': self.client_id, 'value': 0}
        logging.info("... ... announce sonar device [%s]" % device)
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))

        topic = f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/command"
        logging.info("... ... subscribing to [%s] for sonar commands" % topic)
        self.mqtt_client.subscribe(topic, 2)
