#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging
import time

from serial import Serial, SerialException

from common import COLOR_YELLOW, COLOR_DEFAULT, CUBIE_SONAR
from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE, TIMEOUT_UPDATE
from common.network import get_ip_address
from system.base_system import BaseSystem


class SonarSystem(BaseSystem):
    ip_address = None
    communicator = None
    last_update = time.time()
    distance = None
    update_interval = 10

    def __init__(self):
        super().__init__()
        self.execution_mode = CUBIE_SONAR

    def init(self, client_id):
        super().init(client_id)
        self.ip_address = get_ip_address()
        self.update_interval = self.known_device_list['update_interval']
        try:
            self.communicator = Serial(self.known_device_list['device'], 9600)
            self.communicator.flush()
        except SerialException:
            logging.warning(
                f"{COLOR_YELLOW}could not initialise serial communication, running in development mode?{COLOR_DEFAULT}")

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

    def action(self, device):
        logging.info("... ... action for [%s]" % device)
        self.mqtt_client.publish('cubiemedia/' + device['id'].replace(".", "_") + "/distance",
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
                    distance = int(response[response.index("Gap=") + 4:response.index("mm")])

                    if (not self.distance or self.distance != distance) and 200 < distance < 8000:
                        self.distance = distance
                        device = {'id': self.ip_address, 'type': "SONAR", 'value': distance}
                        device_list.append(device)
            self.last_update = time.time()

        data['devices'] = device_list

        if self.last_update < time.time() - self.update_interval:
            self.set_availability(True)
            self.last_update = time.time()
        return data

    def send(self, data):
        raise NotImplemented(f"sending data[{data}] is not implemented")

    def announce(self):
        device = {'id': self.ip_address, 'type': "SONAR"}
        logging.info("... ... announce sonar device [%s]" % device)
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))

        topic = CUBIEMEDIA + self.ip_address.replace(".", "_") + "/command"
        logging.info("... ... subscribing to [%s] for sonar commands" % topic)
        self.mqtt_client.subscribe(topic, 2)
        self.set_availability(True)

    def set_availability(self, state: bool):
        self.mqtt_client.publish(CUBIEMEDIA + self.ip_address.replace(".", "_") + '/online', str(state).lower())

    def save(self, new_device=None):
        if new_device is None:
            super().save()

    def delete(self, device):
        logging.warning(
            "... delete not supported for SONAR devices, please change config locally or via web tool")
