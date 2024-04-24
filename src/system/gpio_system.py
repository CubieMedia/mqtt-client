#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json
import logging
import os
import time

from common import COLOR_YELLOW, COLOR_DEFAULT, CUBIE_GPIO, GPIO_PIN_TYPE_IN, GPIO_PIN_TYPE_OUT, CUBIE_TYPE
from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE, TIMEOUT_UPDATE
from system.base_system import BaseSystem

try:
    from RPi import GPIO
except ImportError as error:
    snap_arch = os.environ.get('SNAP_ARCH')
    if (snap_arch and "arm" in snap_arch) or "arm" in os.uname()[4]:
        logging.warning(
            f"{COLOR_YELLOW} ... could not initialise GPIO, package RPi.GPIO is missing{COLOR_DEFAULT}")
    else:
        logging.warning(
            f"{COLOR_YELLOW} ... could not initialise GPIO, package rpi-gpio-emu is missing{COLOR_DEFAULT}")
    raise error


class GPIOSystem(BaseSystem):
    gpio_control = GPIO

    def __init__(self):
        self.execution_mode = CUBIE_GPIO
        super().__init__()

    def action(self, device: {}) -> bool:
        if device and {'id', 'value'}.issubset(device.keys()):
            logging.info("... ... action for [%s]" % device)
            topic = f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/{device['id']}"
            self.mqtt_client.publish(topic, json.dumps(device['value']))
            return True
        return False

    def send(self, data: {}) -> bool:
        if data and {'id', 'state'}.issubset(data.keys()):
            logging.info("... ... send data[%s] from HA" % data)
            self.gpio_control.output(int(data['id']), GPIO.LOW if int(data['state']) == 1 else GPIO.HIGH)
            return True
        return False

    def save(self, device=None):
        if not device:
            super().save()
        elif device[CUBIE_TYPE] == GPIO_PIN_TYPE_IN or device[CUBIE_TYPE] == GPIO_PIN_TYPE_OUT:
            super().save(device)
        elif 'state' in device:
            for state in device['state']:
                super().save(state)
        else:
            logging.warning(f"... unknown device [{device}], could not save")

    def update(self) -> {}:
        data = {}

        device_list = []
        for device in self.config:
            device_type = str(device[CUBIE_TYPE]).lower()
            if device_type == GPIO_PIN_TYPE_IN:
                value = self.gpio_control.input(device['id'])
            elif device_type == GPIO_PIN_TYPE_OUT:
                value = 1 if self.gpio_control.input(device['id']) == 0 else 0
            else:
                logging.warning("WARN: could not find valid function for device[%s] on update" % device)
                continue

            # pylint: disable=used-before-assignment
            if value != device['value']:
                logging.debug(f"... ... update GPIO [{device['id']}] with value [{value}]")
                device['value'] = value
                device['client_id'] = self.client_id
                device_list.append(device)

        data['devices'] = device_list

        if self.last_update < time.time() - 5:
            self.set_availability(True)
            self.last_update = time.time()
        return data

    def set_availability(self, state: bool):
        super().set_availability(state)
        if state:
            for gpio in self.config:
                self.mqtt_client.publish(
                    f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/{gpio['id']}",
                    str(gpio['value']).lower(), True)

    def init(self):
        super().init()

        self.gpio_control.setmode(GPIO.BCM)
        for device in self.config:
            device_type = str(device[CUBIE_TYPE]).lower()
            if device_type == GPIO_PIN_TYPE_IN:
                logging.info("... set Pin %d as INPUT" % device['id'])
                self.gpio_control.setup(device['id'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            elif device_type == GPIO_PIN_TYPE_OUT:
                logging.info("... set Pin %d as OUTPUT" % device['id'])
                self.gpio_control.setup(device['id'], GPIO.OUT)
                self.gpio_control.output(device['id'], GPIO.HIGH)
            else:
                logging.warning("WARN: could not find valid function for device[%s] on init" % device)

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        super().shutdown()

        logging.info('... cleanup GPIO Pins...')
        if self.gpio_control and len(self.config) > 0:
            self.gpio_control.cleanup()

    def announce(self):
        device = {'id': self.ip_address, CUBIE_TYPE: CUBIE_GPIO, 'client_id': self.client_id,
                  'state': self.config}
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))

        topic = f"{CUBIEMEDIA}/{self.execution_mode}/{self.ip_address.replace('.', '_')}/+/command"
        logging.info("... ... subscribe to [%s] for gpio output commands" % topic)
        self.mqtt_client.subscribe(topic, 2)
        self.set_availability(True)
