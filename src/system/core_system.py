#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging
import time

from common import CUBIEMEDIA
from common import CUBIE_CORE
from common.python import get_configuration
from system.base_system import BaseSystem


class CoreSystem(BaseSystem):
    config = None

    def __init__(self):
        super().__init__()
        self.execution_mode = CUBIE_CORE

    def init(self, client_id):
        logging.info("... init core system")
        super().init(client_id)
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
        logging.info(f"... accounce core system {self.client_id}")

    def set_availability(self, state: bool):
        self.mqtt_client.publish(CUBIEMEDIA + self.ip_address.replace(".", "_") + '/online', str(state).lower())

    def save(self, new_device=None):
        if new_device:
            logging.info(f"... save device [{new_device}] of core system")
            if 'client_id' not in new_device:
                new_device['client_id'] = self.client_id
            if 'type' not in new_device:
                new_device['type'] = self.execution_mode
            local_config = None
            for known_device in self.known_device_list:
                if 'client_id' in known_device:
                    if new_device['client_id'] == known_device['client_id']:
                        local_config = known_device
                        break
            if local_config:
                device_list = [local_config | new_device]
            else:
                device_list = [self.known_device_list[0] | new_device]
            self.known_device_list = device_list
            new_device = None
        if new_device is None:
            super().save()

    def delete(self, device):
        logging.info(f"delete device [{device}] from demo system")
        pass
