#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging
import os
import time

from common import COLOR_YELLOW, COLOR_DEFAULT, CUBIE_GPIO, GPIO_PIN_TYPE_IN, GPIO_PIN_TYPE_OUT
from common.python import install_package
from system.base_system import BaseSystem

snap_arch = os.environ.get('SNAP_ARCH')
if (snap_arch and "arm" in snap_arch) or "arm" in os.uname()[4]:
    try:
        import RPi.GPIO as GPIO
    except (ModuleNotFoundError, RuntimeError) as e:
        install_package("RPi.GPIO")
        import RPi.GPIO as GPIO
else:
    GPIO = None

from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE, TIMEOUT_UPDATE
from common.network import get_ip_address


class GPIOSystem(BaseSystem):
    ip_address = None

    def __init__(self):
        super().__init__()
        self.execution_mode = CUBIE_GPIO
        self.ip_address = get_ip_address()

    def init(self, ip_address):
        super().init(ip_address)
        if not GPIO:
            logging.warning(
                f"{COLOR_YELLOW} ... could not initialise GPIO, running in development mode?{COLOR_DEFAULT}")
        else:
            GPIO.setmode(GPIO.BCM)
            for device in self.known_device_list:
                device_type = str(device['type']).lower()
                if device_type == GPIO_PIN_TYPE_IN:
                    logging.info("... set Pin %d as INPUT" % device['id'])
                    GPIO.setup(device['id'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                elif device_type == GPIO_PIN_TYPE_OUT:
                    logging.info("... set Pin %d as OUTPUT" % device['id'])
                    GPIO.setup(device['id'], GPIO.OUT)
                    GPIO.output(device['id'], GPIO.HIGH)
                else:
                    logging.warning("WARN: could not find valid function for device[%s] on init" % device)

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        logging.info('... cleanup GPIO Pins...')
        if GPIO and len(self.known_device_list) > 0:
            GPIO.cleanup()

    def action(self, device):
        logging.info("... ... action for [%s]" % device)
        topic = f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/{device['id']}"
        self.mqtt_client.publish(topic, json.dumps(device['value']))

    def update(self):
        data = {}

        device_list = []
        if GPIO:
            for device in self.known_device_list:
                device_type = str(device['type']).lower()
                if device_type == GPIO_PIN_TYPE_IN:
                    value = GPIO.input(device['id'])
                elif device_type == GPIO_PIN_TYPE_OUT:
                    value = 1 if GPIO.input(device['id']) == 0 else 0
                else:
                    logging.warning("WARN: could not find valid function for device[%s] on update" % device)
                    continue

                if value != device['value']:
                    # print("%s value %s" % (device['id'], value))
                    device['value'] = value
                    device['client_id'] = self.client_id
                    device_list.append(device)

        data['devices'] = device_list

        if self.last_update < time.time() - TIMEOUT_UPDATE:
            self.set_availability(True)
            self.last_update = time.time()
        return data

    def send(self, data):
        logging.info("... ... send data[%s] from HA" % data)
        if GPIO:
            GPIO.output(int(data['id']), GPIO.LOW if int(data['state'].decode()) == 1 else GPIO.HIGH)

    def announce(self):
        device = {'id': self.ip_address, 'type': CUBIE_GPIO, 'client_id': self.client_id, 'state': self.known_device_list}
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))

        topic = f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/+/command"
        logging.info("... ... subscribing to [%s] for gpio output commands" % topic)
        self.mqtt_client.subscribe(topic, 2)
        self.set_availability(True)

    def set_availability(self, state: bool):
        super().set_availability(state)
        if state:
            for gpio in self.known_device_list:
                self.mqtt_client.publish(
                    f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/{gpio['id']}",
                    str(gpio['value']).lower())

    def save(self, new_device=None):
        if new_device is None:
            super().save()

    def delete(self, device):
        logging.warning("... delete not supported for GPIO devices, please change config locally")
