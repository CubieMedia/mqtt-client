#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging

from common import CUBIE_CORE, DEFAULT_TOPIC_ANNOUNCE
from system.base_system import BaseSystem


class CoreSystem(BaseSystem):

    def __init__(self):
        self.execution_mode = CUBIE_CORE
        super().__init__()

    def announce(self):
        device = self.core_config
        logging.info("... ... announce core device [%s]" % device)
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))

        self.set_availability(True)

    def save(self, device: {} = None):
        is_new_device = True
        if device:
            for core_config in self.config:
                if 'id' not in device or device['id'] == core_config['id']:
                    if sorted(device.items()) != sorted(core_config.items()):
                        index = self.config.index(core_config)
                        for key in device:
                            core_config[key] = device[key]
                        logging.info(f"... save config [{core_config}] for core system")
                        self.config[index] = core_config
                    is_new_device = False

        if device and is_new_device:
            self.config.append(device)
        super().save()

    def delete(self, device):
        logging.info(f"... delete device [{device}] from core system")
        for core_config in self.config:
            if 'id' in core_config:
                if str(core_config['id']) == str(device['id']) and str(device['id']) != str(self.ip_address):
                    self.config.remove(core_config)
                    self.save()
                    return

        logging.warning(f"could not find config [{device}] or this is my own config, did not delete anything")
