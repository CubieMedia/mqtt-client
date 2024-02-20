#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging

from common import CUBIE_CORE, DEFAULT_TOPIC_ANNOUNCE
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

        if 'mode' in device and device['mode'] == 'update':
            if CUBIE_TYPE in device and device[CUBIE_TYPE] == self.execution_mode:
                logging.error(f"TEST [{device}]")

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

    def save(self, new_device: {} = None):
        should_save = False if new_device else True
        if new_device:
            if 'id' not in new_device:
                new_device['id'] = self.ip_address
            for core_config in self.known_device_list:
                if new_device['id'] == core_config['id']:
                    if sorted(new_device.items()) != sorted(core_config.items()):
                        logging.info(f"... save config [{new_device}] for core system")
                        index = self.known_device_list.index(core_config)
                        for key in new_device:
                            core_config[key] = new_device[key]
                        self.known_device_list[index] = core_config
                        should_save = True
                    new_device = None
                    break

            if new_device:
                self.known_device_list.append(new_device)
                should_save = True

        if should_save:
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
