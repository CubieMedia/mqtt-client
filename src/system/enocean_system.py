#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import copy
import json
import logging
import platform
import queue
import time
from threading import Timer

from enocean.communicators.serialcommunicator import SerialCommunicator
from enocean.protocol.constants import PACKET, RORG
from serial import SerialException

from common import *
from common.python import get_configuration
from system.base_system import BaseSystem


class EnoceanSystem(BaseSystem):
    serial_port = None
    communicator = None
    update_timeout = 30
    timers = {}

    def __init__(self):
        self.execution_mode = CUBIE_ENOCEAN
        super().__init__()

    def action(self, device):
        if device and {'id', 'state', 'dbm'}.issubset(device.keys()):
            should_save = False

            for known_device in self.config:
                if str(device['id']).upper() == str(known_device['id']).upper():
                    if known_device['client_id'] != self.client_id:
                        if device['dbm'] > known_device['dbm']:
                            device['client_id'] = self.client_id
                            logging.info("... ... device with better connection, announce [%s]" % device)
                            self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))
                            return False
                        logging.debug("... ... device is not managed by this gateway [%s]" % device)
                        return True
                    if str(device[CUBIE_TYPE]).upper() == "RPS":
                        for topic in device['state']:
                            if 'state' not in known_device or len(known_device['state']) == 0 or \
                                    (topic in known_device['state'] and device['state'][topic] != known_device['state'][
                                        topic]):
                                channel_topic = f"{CUBIEMEDIA}/{self.execution_mode}/{str(device['id']).lower()}/{topic}"
                                value = device['state'][topic]
                                if value == 1:
                                    self._create_timer_for(channel_topic)
                                else:
                                    logging.info("... ... action for [%s]" % channel_topic)
                                    if channel_topic in self.timers and self.timers[channel_topic] is not True:
                                        self.mqtt_client.publish(channel_topic, 1)
                                        timer = self.timers[channel_topic]
                                        timer.cancel()
                                        del self.timers[channel_topic]
                                        short_push_timer = Timer(0.5, self.mqtt_client.publish,
                                                                  [channel_topic, 0, True])
                                        short_push_timer.start()
                                    else:
                                        if channel_topic in self.timers:
                                            del self.timers[channel_topic]
                                        self.mqtt_client.publish(channel_topic + "/longpush", 0, True)
                                should_save = True
                        known_device['state'] = device['state']
                        if device['dbm'] > known_device['dbm']:
                            known_device['dbm'] = device['dbm']
                        if should_save:
                            self.save(device)
                    else:
                        logging.debug("... ... send message for [%s]" % device['id'])
                        self.mqtt_client.publish(
                            f"{CUBIEMEDIA}/{self.execution_mode}/{str(device['id']).lower()}",
                            json.dumps(device['state']),
                            True)
                    return True

            device['client_id'] = self.client_id
            logging.info("... ... unknown device, announce [%s]" % device)
            self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))
        else:
            logging.warning(f"could not execute action on device [{device}]")
        return False

    def update(self) -> {}:
        try:
            if self.communicator:
                data = {}
                packet = self.communicator.receive.get(block=False, timeout=1)
                if packet.packet_type == PACKET.RADIO_ERP1:
                    sensor = {'id': packet.sender_hex.replace(':', '').lower(), 'dbm': packet.dBm}
                    if packet.rorg == RORG.RPS:
                        sensor[CUBIE_TYPE] = 'RPS'
                        sensor['state'] = self._get_rps_state_from2(packet)
                        data['devices'] = [sensor]
                    elif packet.rorg == RORG.BS4:
                        sensor[CUBIE_TYPE] = 'TEMP'
                        sensor['state'] = self._get_temp_state_from(packet)
                        data['devices'] = [sensor]
                    else:
                        logging.error(f"device type (RORG: {packet.rorg}) not supported")
                else:
                    logging.error(f"packet type ({packet.packet_type}) not supported")

                if self.last_update < time.time() - TIMEOUT_UPDATE:
                    self.set_availability(True)
                    self.last_update = time.time()
                return data
        except queue.Empty:
            pass
        except Exception as e:
            logging.error("ERROR on update: %s" % e)
        return {}

    def set_availability(self, state: bool):
        for device in self.config:
            if device['client_id'] == self.client_id:
                self.mqtt_client.publish(f"{CUBIEMEDIA}/{self.execution_mode}/{str(device['id']).lower()}/online",
                                         str(state).lower())
                if state and 'state' in device:
                    for topic in device['state']:
                        self.mqtt_client.publish(
                            f"{CUBIEMEDIA}/{self.execution_mode}/{str(device['id']).lower()}/{topic}",
                            str(device['state'][topic]).lower(), True)
                        self.mqtt_client.publish(
                            f"{CUBIEMEDIA}/{self.execution_mode}/{str(device['id']).lower()}/{topic}/longpush", str(0),
                            True)

    def init(self):
        super().init()

        self._open_communicator()

        if self.communicator:
            logging.info("... starting serial communicator")
            self.communicator.start()
            time.sleep(0.100)
            self.set_availability(True)

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        super().shutdown()

        if self.communicator:
            logging.info('... stopping Enocean Communicator...')
            self.communicator.stop()
            time.sleep(1)

    def announce(self):
        for device in self.config:
            if device['client_id'] == self.client_id:
                logging.info("... ... announce device [%s]" % device['id'])
                self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))
                if 'state' in device:
                    for topic in device['state']:
                        if device['state'][topic] == 1:
                            channel_topic = f"{CUBIEMEDIA}/{self.execution_mode}/{str(device['id']).lower()}/{topic}"
                            self._create_timer_for(channel_topic, True)
        self.last_update = 0

    def save(self, device=None):
        if device and {'id', 'dbm'}.issubset(device.keys()):
            if (str(device[CUBIE_TYPE]).upper() == "RPS" or str(
                    device[CUBIE_TYPE]).upper() == "TEMP") and self.core_config['learn_mode']:
                add = True
                for known_device in self.config:
                    if str(device['id']).upper() == str(known_device['id']).upper():
                        add = False
                        if device['dbm'] > known_device['dbm']:
                            device = copy.copy(device)
                            del device['state']
                            logging.info("... ... replace device[%s]" % device)
                            self.config[self.config.index(known_device)] = device
                            add = True
                        break

                if add:
                    logging.info(f"... ... adding new/changed device[{device['id']}]")
                    super().save(device)
                    self.announce()
            else:
                logging.warning(f"could not save unknown device [{device}]")
        else:
            super().save(device)

        if device and 'state' in device:
            self.action(device)

    @staticmethod
    def _get_temp_state_from(packet):
        packet.parse_eep(0x02, 0x05)
        temperature = round(packet.parsed['TMP']['value'], 1)
        return {"value": temperature}

    @staticmethod
    def _get_rps_state_from2(packet):
        state = {}
        for k in packet.parse_eep(0x02, 0x02):
            if k == 'R1':
                button_action = int(packet.parsed[k]['raw_value'])
            if k == 'R2':
                button_action_2 = int(packet.parsed[k]['raw_value'])
            if k == 'EB':
                energy_bow_active = int(packet.parsed[k]['raw_value']) == 1
            if k == 'SA':
                has_second_action = int(packet.parsed[k]['raw_value']) == 1

        logging.debug(f"Action: {button_action}, SA: {has_second_action}, Action2: {button_action_2}, EB: {energy_bow_active}")

        if energy_bow_active:
            if button_action == 0:
                state['a2'] = 1
            elif button_action == 1:
                state['a1'] = 1
            elif button_action == 2:
                state['b2'] = 1
            elif button_action == 3:
                state['b1'] = 1

            if has_second_action:
                if button_action_2 == 2:
                    state['b2'] = 1
                elif button_action_2 == 3:
                    state['b1'] = 1
        else:
            state['a1'] = 0
            state['a2'] = 0
            state['b1'] = 0
            state['b2'] = 0

        logging.debug(state)

        return state

    @staticmethod
    def _get_rps_state_from(packet):
        state = {}
        data = packet.data[1]
        sa = data & 0x40 >> 6
        button_action = data & 0xE0
        energy_bow = (data & 0x10) >> 4

        logging.debug("SA: %s, Action: %02X, EB: %s" % (sa, button_action, energy_bow))
        if button_action == 0xE0:
            state['a1'] = energy_bow
        elif energy_bow == 1:
            if button_action == 0x00:
                state['a2'] = 1
            elif button_action == 0x20:
                state['a1'] = 1

            if sa == 0:
                if button_action == 0x40:
                    state['b2'] = 1
                elif button_action == 0x60:
                    state['b1'] = 1
            else:
                button_action_channel_2 = data & 0x03
                if button_action_channel_2 == 0x01:
                    state['b2'] = 1
                elif button_action_channel_2 == 0x03:
                    state['b1'] = 1
        else:
            state['a1'] = 0
            state['a2'] = 0
            state['b1'] = 0
            state['b2'] = 0

        return state

    def _create_timer_for(self, channel_topic, force=False):
        if channel_topic not in self.timers:
            timer = Timer(0.8, self._long_push_timer, [channel_topic])
            self.timers[channel_topic] = timer
            timer.start()
        elif force:
            logging.info("... ... sending longpush [%s]" % channel_topic)
            self.mqtt_client.publish(channel_topic + "/longpush", 1, True)

    def _long_push_timer(self, channel_topic):
        self.timers[channel_topic] = True
        logging.info("... ... sending longpush [%s]" % channel_topic)
        self.mqtt_client.publish(channel_topic + "/longpush", 1, True)

        topic_array = channel_topic.split('/')
        device_id = topic_array[1]
        button = topic_array[2]
        device = None
        for known_device in self.config:
            if device_id == known_device['id']:
                device = known_device
                break

        if device is not None and 'channel_config' in device:
            channel_config = device['channel_config']
            logging.info(f"... ... ... found config[{channel_config}] for device[{device_id}] and button[{button}]")
            if button[0] in channel_config:
                device_topic = channel_config[button[0]]
                if 'dimmer' in device_topic:
                    value = 5 if button[1] == '1' else 95
                    while channel_topic in self.timers:
                        self.mqtt_client.publish(device_topic, '{"turn": "on","brightness": ' + str(value), True)
                        value += 10 if button[1] == '1' else -10
                        time.sleep(0.5)
                else:
                    logging.warning("WARN: unknown device[%s]" % device_topic)

    def _open_communicator(self):
        try:
            serial_json = get_configuration(CUBIE_SERIAL)[0]
            if serial_json[CUBIE_TYPE] == CUBIE_SERIAL and CUBIE_DEVICE in serial_json:
                self.communicator = SerialCommunicator(ENOCEAN_PORT)
        except SerialException:
            if "arm" in platform.machine():
                logging.warning(
                    f"{COLOR_YELLOW}could not initialise serial communication, is the plug [serial-port] connected to [bt-serial]?{COLOR_DEFAULT}")
            else:
                logging.warning(
                    f"{COLOR_YELLOW}could not initialise serial communication, running in development mode?{COLOR_DEFAULT}")
