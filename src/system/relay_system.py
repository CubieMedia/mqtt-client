#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import logging
import socket
import threading
import time

import requests

from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE, RELAY_USERNAME, RELAY_PASSWORD, STATE_UNKNOWN, \
    TIMEOUT_UPDATE, TIMEOUT_UPDATE_SEND, CUBIE_RELAY, CUBIE_TYPE
from system.base_system import BaseSystem

DISCOVERY_MESSAGE = "DISCOVER_RELAIS_MODULE".encode()
DESTINATION_ADDRESS = ('<broadcast>', 30303)


class RelaySystem(BaseSystem):
    module_list = []
    subscription_list = []
    scan_thread = threading.Thread()
    scan_thread_event = threading.Event()
    discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    discovery_socket.settimeout(1)

    def __init__(self):
        self.execution_mode = CUBIE_RELAY
        super().__init__()

    def action(self, device: {}) -> bool:
        if 'id' in device:
            if not device['id'] in self.subscription_list:
                logging.info("... ... subscribing to [%s] for commands" % device['id'])
                self.mqtt_client.subscribe(f"{CUBIEMEDIA}/{self.execution_mode}/{device['id'].replace('.', '_')}/+/command",
                                           2)
                self.subscription_list.append(device['id'])

            for known_device in self.config:
                if device['id'] == known_device['id'] and 'state' in device:
                    for relay in device['state']:
                        if not device['state'][relay] == known_device['state'][relay]:
                            logging.info("... ... action for [%s] Relay [%s] -> [%s]" % (
                                device['id'], relay, device['state'][relay]))
                            self.mqtt_client.publish(
                                f"{CUBIEMEDIA}/{self.execution_mode}/{device['id'].replace('.', '_')}/{relay}",
                                device['state'][relay], True)
                            known_device['state'][relay] = device['state'][relay]
                    return True

            if self.core_config['learn_mode']:
                logging.info("... ... unknown device, announce [%s]" % device['id'])
                self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))
        else:
            logging.warning(f"... received action with wrong data [{device}]")
        return False

    def send(self, data):
        toggle = False
        for known_device in self.config:
            if data['ip'] == known_device['id']:
                if 'toggle' in known_device and int(data['id']) in known_device['toggle']:
                    toggle = True
        logging.debug("... ... send data[%s] from HA with toggle[%s]" % (data, toggle))
        self._set_status(data['ip'], data['id'], data['state'], toggle)
        self.last_update = -1 if toggle else 0

    def update(self):
        data = {}
        if self.last_update < time.time() - TIMEOUT_UPDATE:
            relayboard_list = []
            send_data = False
            for module in self.module_list:
                known_device = None
                for temp_device in self.config:
                    if module == temp_device['id']:
                        known_device = temp_device

                relayboard = {'id': str(module), CUBIE_TYPE: CUBIE_RELAY, 'client_id': self.client_id}
                status_list = self._read_status(module)
                relay_state_list = {}
                relay_state_changed_list = {}
                count = 1
                for status in status_list:
                    relay_state_list[str(count)] = status
                    if known_device is None or 'state' not in known_device or status != known_device['state'][
                        str(count)] or self.last_update < time.time() - TIMEOUT_UPDATE_SEND:
                        relay_state_changed_list[str(count)] = status
                        send_data = True
                    count += 1

                if send_data:
                    relayboard['state'] = relay_state_changed_list
                    relayboard_list.append(relayboard)

            if send_data:
                data['devices'] = relayboard_list
            if self.last_update < 0:
                self.last_update = time.time() - int(TIMEOUT_UPDATE / 1.4)
            else:
                self.last_update = time.time()
        return data

    def set_availability(self, state: bool):
        for device in self.config:
            self.mqtt_client.publish(f"{CUBIEMEDIA}/{self.execution_mode}/{device['id'].replace('.', '_')}/online",
                                     str(state).lower())

            if 'state' in device:
                for relay in device['state']:
                    self.mqtt_client.publish(
                        f"{CUBIEMEDIA}/{self.execution_mode}/{device['id'].replace('.', '_')}/{relay}",
                        device['state'][relay], True)

    def init(self):
        super().init()

        logging.info("... starting scan thread")
        self.scan_thread = threading.Thread(target=self._run)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        logging.info("... stopping scan thread...")
        self.scan_thread_event.set()
        self.scan_thread.join()

        super().shutdown()

    def announce(self):
        for device in self.config:
            logging.info("... ... announce device [%s]" % device['id'])
            self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))
            logging.info("... ... subscribing to [%s] for commands" % device['id'])
            self.mqtt_client.subscribe(f"{CUBIEMEDIA}/{self.execution_mode}/{device['id'].replace('.', '_')}/+/command",
                                       2)
            if not device['id'] in self.subscription_list:
                self.subscription_list.append(device['id'])

        self.set_availability(True)

    def save(self, new_device=None):
        should_save = False
        if new_device is not None:
            if new_device[CUBIE_TYPE] == CUBIE_RELAY and self.core_config['learn_mode']:
                add = True
                for known_device in self.config:
                    if new_device['id'] == known_device['id']:
                        add = False
                        break
                if add:
                    self.config.append(new_device)
                    self.update()
                    should_save = True
        else:
            should_save = True

        if should_save:
            super().save()

    def load(self):
        super().load()
        self.module_list = []
        for device in self.config:
            self.module_list.append(device['id'])
        self.update()

    def _run(self):
        self.scan_thread_event = threading.Event()

        buf = []
        while not self.scan_thread_event.is_set():
            try:
                if not len(buf):
                    logging.info("... ... sending discovery message for relay boards")
                    self.discovery_socket.sendto(DISCOVERY_MESSAGE, DESTINATION_ADDRESS)
                    self.scan_thread_event.wait(1)
                (buf, address) = self.discovery_socket.recvfrom(30303)
                logging.debug(f"... received from {address}: {buf}")
                if "ETH008" in str(buf):
                    if not address[0] in self.module_list:
                        logging.info(f"... ... found new module[{address[0]}]")
                        self.module_list.append(address[0])
                        self.last_update = -1
                        continue
                self.scan_thread_event.wait(1)
            except (socket.timeout, OSError):
                buf = []
                self.scan_thread_event.wait(TIMEOUT_UPDATE_SEND)

        self.discovery_socket.close()
        return True

    def _read_status(self, ip):
        status_list = []
        auth = (RELAY_USERNAME, RELAY_PASSWORD)

        url = "http://" + str(ip) + "/status.xml"
        try:
            r = requests.get(url, auth=auth, timeout=1)

            content = r.text
            logging.debug(f"... ... content:\n{content}")
            self.mqtt_client.publish(f"{CUBIEMEDIA}/{self.execution_mode}/{str(ip).replace('.', '_')}/online", 'true')
            for line in content.splitlines():
                if "relay" in line:
                    status = line[line.index(">") + 1:line.index("</")]
                    if status == "1" or status == "0":
                        status_list.append(status)
                    else:
                        status_list.append(STATE_UNKNOWN)
                        logging.warning("... ... WARN: state [%s] unknown" % status)

        except ConnectionError:
            logging.info(f"ERROR ... could not read status from relay board [{ip}]")
            self.mqtt_client.publish(f"{CUBIEMEDIA}/{self.execution_mode}/{str(ip).replace('.', '_')}/online", 'false')
        finally:
            return status_list

    @staticmethod
    def _set_status(ip, relay, state, toggle: bool = False):
        auth = (RELAY_USERNAME, RELAY_PASSWORD)

        url = "http://" + str(ip) + "/io.cgi?"
        url += "DOA" if state == b'1' or str(state) == "1" else "DOI"
        url += relay
        if toggle:
            url += '=30'  # + str(int(toggle) * 10)
        try:
            requests.get(url, auth=auth)
        except ConnectionError:
            logging.info(f"ERROR ... could not set value on relay board [{ip}]")
