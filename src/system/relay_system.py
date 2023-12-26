#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import logging
import socket
import threading
import time

import requests

from common import CUBIEMEDIA, DEFAULT_TOPIC_ANNOUNCE, RELAY_USERNAME, RELAY_PASSWORD, STATE_UNKNOWN, \
    TIMEOUT_UPDATE, TIMEOUT_UPDATE_SEND, CUBIE_RELAY
from system.base_system import BaseSystem


class RelaySystem(BaseSystem):
    module_list = []
    subscription_list = []
    scan_thread = threading.Thread()
    search_thread_event = threading.Event()

    def __init__(self):
        super().__init__()
        self.execution_mode = CUBIE_RELAY

    def action(self, device):
        if not device['id'] in self.subscription_list:
            logging.info("... ... subscribing to [%s] for commands" % device['id'])
            self.mqtt_client.subscribe(CUBIEMEDIA + device['id'].replace(".", "_") + "/+/command", 2)
            self.subscription_list.append(device['id'])

        for known_device in self.known_device_list:
            if device['id'] == known_device['id']:
                for relay in device['state']:
                    # print(f"device[{device['state'][relay]}] - known_device[{known_device['state'][relay]}]")
                    if not device['state'][relay] == known_device['state'][relay]:
                        logging.info("... ... action for [%s] Relay [%s] -> [%s]" % (
                            device['id'], relay, device['state'][relay]))
                        self.mqtt_client.publish(CUBIEMEDIA + device['id'].replace(".", "_") + "/" + relay,
                                                 device['state'][relay])
                        known_device['state'][relay] = device['state'][relay]
                return True

        logging.info("... ... unknown device, announce [%s]" % device['id'])
        self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))
        return False

    def send(self, data):
        toggle = False
        for known_device in self.known_device_list:
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
            # print("... update data for all modules")
            for module in self.module_list:
                known_device = None
                for temp_device in self.known_device_list:
                    if module == temp_device['id']:
                        known_device = temp_device

                relayboard = {'id': str(module), 'type': CUBIE_RELAY, 'client_id': self.client_id}
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
        for device in self.known_device_list:
            self.mqtt_client.publish(CUBIEMEDIA + device['id'].replace(".", "_") + '/online', str(state).lower())

    def init(self, client_id):
        super().init(client_id)
        logging.info("... starting scan thread")
        self.scan_thread = threading.Thread(target=self._run)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        logging.info("... stopping scan thread...")
        self.search_thread_event.set()
        self.scan_thread.join()

    def announce(self):
        for device in self.known_device_list:
            logging.info("... ... announce device [%s]" % device['id'])
            self.mqtt_client.publish(DEFAULT_TOPIC_ANNOUNCE, json.dumps(device))
            logging.info("... ... subscribing to [%s] for commands" % device['id'])
            self.mqtt_client.subscribe(CUBIEMEDIA + device['id'].replace(".", "_") + "/+/command", 2)
            if not device['id'] in self.subscription_list:
                self.subscription_list.append(device['id'])

    def save(self, new_device=None):
        should_save = False
        if new_device is not None:
            if new_device['type'] == CUBIE_RELAY and self.learn_mode:
                add = True
                for known_device in self.known_device_list:
                    if new_device['id'] == known_device['id']:
                        add = False
                        break
                if add:
                    self.known_device_list.append(new_device)
                    self.update()
                    should_save = True
        else:
            should_save = True

        if should_save:
            super().save()

    def load(self):
        super().load()
        for device in self.known_device_list:
            self.module_list.append(device['id'])
        self.update()

    def _run(self):
        self.search_thread_event = threading.Event()

        msg = "DISCOVER_RELAIS_MODULE"
        destination = ('<broadcast>', 30303)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(1)
        s.sendto(msg.encode(), destination)
        while not self.search_thread_event.is_set():
            try:
                (buf, address) = s.recvfrom(30303)
                if not len(buf):
                    break
                #      print("... received from %s: %s" %(address, buf))
                if "ETH008" in str(buf):
                    if not address[0] in self.module_list:
                        logging.info(f"... found new module[{address[0]}]")
                        self.module_list.append(address[0])
                continue
            except socket.timeout:
                pass

            self.search_thread_event.wait(60)
            s.sendto(msg.encode(), destination)

        return True

    def _read_status(self, ip):
        status_list = []
        auth = (RELAY_USERNAME, RELAY_PASSWORD)

        url = "http://" + str(ip) + "/status.xml"
        try:
            r = requests.get(url, auth=auth, timeout=1)

            content = r.text
            #  print("... ... content: " + str(content))
            self.mqtt_client.publish(CUBIEMEDIA + str(ip).replace(".", "_") + '/online', 'true')
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
            self.mqtt_client.publish(CUBIEMEDIA + str(ip).replace(".", "_") + '/online', 'false')
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
