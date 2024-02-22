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

    def save(self, new_device: {} = None):
        should_save = False if new_device else True
        if new_device:
            if 'id' not in new_device:
                new_device['id'] = self.ip_address
            for core_config in self.config:
                if new_device['id'] == core_config['id']:
                    if sorted(new_device.items()) != sorted(core_config.items()):
                        logging.info(f"... save config [{new_device}] for core system")
                        index = self.config.index(core_config)
                        for key in new_device:
                            core_config[key] = new_device[key]
                        self.config[index] = core_config
                        should_save = True
                    new_device = None
                    break

            if new_device:
                self.config.append(new_device)
                should_save = True

        if should_save:
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
