#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging
import json

from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE, CUBIE_RELOAD, DEFAULT_TOPIC_COMMAND
from common import CUBIE_CORE
from common.python import get_configuration, get_core_configuration
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
        device = get_core_configuration(self.ip_address)
        logging.info("... ... announce core device [%s]" % device)
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))

        self.set_availability(True)

    def save(self, new_device=None):
        if new_device:
            if 'id' in new_device:
                logging.info(f"... save device [{new_device}] of core system")
                for core_config in self.known_device_list:
                    if new_device['id'] == core_config['id']:
                        self.known_device_list[self.known_device_list.index(core_config)] = new_device
                        new_device = None

                if new_device:
                    self.known_device_list.append(new_device)

        if new_device is None:
            super().save()

    def delete(self, device):
        logging.info(f"... delete device [{device}] from core system")
        for core_config in self.known_device_list:
            if 'id' in core_config:
                if str(core_config['id']) == str(device['id']) and str(device['id']) != str(self.ip_address):
                    self.known_device_list.remove(core_config)
                    self.save()
                    return

        logging.warning(f"could not find config [{device}] or this is my own config, did not delete anything")
