#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging
import json

from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE, CUBIE_RELOAD, DEFAULT_TOPIC_COMMAND
from common import CUBIE_CORE
from common.python import get_configuration
from system.base_system import BaseSystem


class CoreSystem(BaseSystem):
    config = None

    def __init__(self):
        super().__init__()
        self.execution_mode = CUBIE_CORE

    def init(self, ip_address):
        super().init(ip_address)
        logging.info("... init core system")
        self.config = get_configuration(CUBIE_CORE)

    def shutdown(self):
        logging.info("... shutdown core system")
        pass

    def action(self, device):
        should_save = False
        logging.info(device)

        if 'mode' in device and device['mode'] == 'update':
            if 'type' in device and device['type'] == self.execution_mode:
                logging.error("TEST")

        if should_save:
            self.save(device)

    def update(self):
        data = {}

        return data

    def send(self, data):
        logging.info(f"... send data [{data}] to devices of core system")

    def announce(self):
        device = {'id': self.ip_address, 'type': CUBIE_CORE, 'client_id': self.client_id}
        logging.info("... ... announce core device [%s]" % device)
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))

        self.set_availability(True)

    def save(self, new_device=None):
        if new_device:
            logging.info(f"... save device [{new_device}] of core system")
            if 'client_id' not in new_device:
                new_device['client_id'] = self.client_id
            if 'type' not in new_device:
                new_device['type'] = self.execution_mode
            device_list = self.known_device_list | new_device
            self.known_device_list = device_list
            new_device = None

        if new_device is None:
            super().save()

        logging.info("... send reload command for all services")
        self.mqtt_client.publish(DEFAULT_TOPIC_COMMAND, CUBIE_RELOAD)

    def delete(self, device):
        logging.info(f"delete device [{device}] from demo system")
        pass
