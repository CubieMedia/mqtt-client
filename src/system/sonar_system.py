#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging
import time

from serial import Serial, SerialException

from common import COLOR_YELLOW, COLOR_DEFAULT, CUBIE_SONAR, SONAR_PORT, DEFAULT_OFFSET
from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE
from common.network import get_ip_address
from system.base_system import BaseSystem


class SonarSystem(BaseSystem):
    ip_address = None
    communicator = None
    last_update = time.time()
    distance = None
    update_interval = 1
    offset = 0
    trigger_offset = 5

    def __init__(self):
        super().__init__()
        self.execution_mode = CUBIE_SONAR

    def init(self, ip_address):
        super().init(ip_address)
        self.ip_address = get_ip_address()
        self.update_interval = self.known_device_list[
            'update_interval'] if 'update_interval' in self.known_device_list else 1
        self.offset = self.known_device_list[
            'offset'] if 'offset' in self.known_device_list else 0
        self.trigger_offset = self.known_device_list[
            'trigger_offset'] if 'trigger_offset' in self.known_device_list else DEFAULT_OFFSET
        try:
            self.communicator = Serial(
                self.known_device_list['device'] if 'device' in self.known_device_list else SONAR_PORT, 9600)
            self.communicator.flush()
        except SerialException:
            logging.warning(
                f"{COLOR_YELLOW}could not initialise serial communication, running in development mode?{COLOR_DEFAULT}")

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

    def action(self, device):
        logging.info("... ... action for [%s]" % device)
        self.mqtt_client.publish(f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/distance",
                                 json.dumps(device['value']))

    def update(self):
        data = {}

        device_list = []
        if self.communicator and self.last_update < time.time() - 1:
            self.communicator.write(0x01)
            self.communicator.flushOutput()

            if self.communicator.inWaiting() > 0:
                response = str(self.communicator.read(self.communicator.inWaiting()))
                if "Gap=" in response:
                    distance = int(response[response.index("Gap=") + 4:response.index("mm")]) + self.offset

                    if not self.distance or abs(self.distance - distance) > self.trigger_offset:
                        if 200 <= distance - self.offset <= 8000:
                            self.distance = distance
                            device = {'id': self.ip_address, 'type': "SONAR", 'value': self.distance}
                            device_list.append(device)
                        else:
                            logging.warning(
                                f"Distance [{distance}] is out of range, object too close or cable disconnected")
                else:
                    logging.warning(f"Could not find [Gap] in response[{response}]")

            self.last_update = time.time()

        data['devices'] = device_list

        if self.last_update < time.time() - self.update_interval:
            self.set_availability(True)
            self.last_update = time.time()
        return data

    def send(self, data):
        raise NotImplemented(f"sending data[{data}] is not implemented")

    def announce(self):
        device = {'id': self.ip_address, 'type': "SONAR", 'client_id': self.client_id}
        logging.info("... ... announce sonar device [%s]" % device)
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))

        topic = f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/command"
        logging.info("... ... subscribing to [%s] for sonar commands" % topic)
        self.mqtt_client.subscribe(topic, 2)
        self.set_availability(True)

    def save(self, new_device=None):
        if new_device is None:
            super().save()

    def delete(self, device):
        logging.warning(
            "... delete not supported for SONAR devices, please change config locally or via web tool")
