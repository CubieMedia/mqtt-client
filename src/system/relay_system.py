#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import logging
import socket
import threading
import time

import requests
from requests import ConnectionError

from common import MQTT_CUBIEMEDIA, RELAY_USERNAME, RELAY_PASSWORD, \
    STATE_UNKNOWN, \
    TIMEOUT_UPDATE_AVAILABILITY, TIMEOUT_UPDATE_RELAY, CUBIE_RELAY, CUBIE_TYPE, QOS, \
    MQTT_HOMEASSISTANT_PREFIX
from common.homeassistant import MQTT_LIGHT, PAYLOAD_SWITCH_ACTOR, \
    MQTT_NAME, MQTT_COMMAND_TOPIC, MQTT_STATE_TOPIC, MQTT_AVAILABILITY_TOPIC, MQTT_UNIQUE_ID, \
    MQTT_DEVICE, MQTT_DEVICE_IDS, MQTT_DEVICE_DESCRIPTION
from system.base_system import BaseSystem

DISCOVERY_MESSAGE = "DISCOVER_RELAIS_MODULE".encode()
DESTINATION_ADDRESS = ('<broadcast>', 30303)


class RelaySystem(BaseSystem):
    relay_board_list = []
    all_relay_boards_scanned = False
    index_of_current_relay_board = 0
    scan_thread = threading.Thread()
    scan_thread_event = threading.Event()
    discovery_socket = None

    def __init__(self):
        self.execution_mode = CUBIE_RELAY
        super().__init__()

    def action(self, device: {}) -> bool:
        if all(attribute in device for attribute in ['id', 'state']):
            for known_device in self.config:
                if device['id'] == known_device['id']:
                    for relay in device['state']:
                        logging.info("... ... action for [%s] Relay [%s] -> [%s]" % (
                            device['id'], relay, device['state'][relay]))
                        self.mqtt_client.publish(
                            f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{device['id'].replace('.', '_')}/{relay}",
                            device['state'][relay], True)
                        known_device['state'][relay] = device['state'][relay]
                    return True
        else:
            logging.warning(f"... received action with wrong data [{device}]")
        return False

    def send(self, data) -> bool:
        toggle = False
        for known_device in self.config:
            if data['ip'] == known_device['id']:
                self.index_of_current_relay_board = self.config.index(known_device)
                if 'toggle' in known_device and int(data['id']) in known_device['toggle']:
                    toggle = True
                logging.debug("... ... send data[%s] from HA with toggle[%s]" % (data, toggle))
                self._set_status(data['ip'], data['id'], data['state'], toggle)
                self.last_update = -1 if toggle else 0
                return True

        return super().send(data)

    def update(self):
        data = {}
        if self.last_update < time.time() - TIMEOUT_UPDATE_RELAY and len(self.relay_board_list) > 0:
            relay_board = self.relay_board_list[self.index_of_current_relay_board]
            logging.info(f"... ... updating relay board [{relay_board}]")
            known_device = None
            for temp_device in self.config:
                if relay_board == temp_device['id']:
                    known_device = temp_device

            relay_board_json = {'id': str(relay_board), CUBIE_TYPE: CUBIE_RELAY,
                                'client_id': self.client_id}
            status_list = self._read_status(relay_board)
            if known_device:
                logging.debug("... ... ... scanning for changes on known device")
                relay_state_changed_list = {}
                send_data = False
                index = 0
                for status in status_list:
                    if status != known_device['state'][index]:
                        relay_state_changed_list[str(index + 1)] = status
                        send_data = True
                    index += 1

                if send_data:
                    logging.debug("... ... ... found changes, sending action data")
                    relay_board_json['state'] = relay_state_changed_list
                    data['devices'] = [relay_board_json]
            else:
                logging.debug("... ... ... saving new device with state")
                relay_board_json['state'] = status_list
                self.save(relay_board_json)

            self.index_of_current_relay_board += 1
            if self.index_of_current_relay_board >= len(self.relay_board_list):
                self.index_of_current_relay_board = 0
                self.all_relay_boards_scanned = True

            if self.all_relay_boards_scanned:
                if self.last_update < 0:
                    self.last_update = time.time() - int(TIMEOUT_UPDATE_RELAY * 0.3)
                else:
                    self.last_update = time.time()
                self.set_availability(True)
        return data

    def set_availability(self, state: bool):
        super().set_availability(state)
        for device in self.config:
            self.mqtt_client.publish(
                f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{device['id'].replace('.', '_')}/online",
                str(state).lower())

    def init(self):
        super().init()

        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.settimeout(1)

        logging.info("... starting scan thread")
        self.scan_thread = threading.Thread(target=self._run)
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        if self.scan_thread.is_alive():
            logging.info("... stopping scan thread...")
            self.scan_thread_event.set()
            self.scan_thread.join()

        super().shutdown()

    def announce(self):
        super().announce()
        for device in self.config:
            self.announce_device(device)
        self.set_availability(True)

    def save(self, device=None):
        should_save = False
        if device is not None:
            if device[CUBIE_TYPE] == CUBIE_RELAY and self.system_config['devices_can_be_added']:
                add = True
                for known_device in self.config:
                    if device['id'] == known_device['id']:
                        add = False
                        break
                if add:
                    self.config.append(device)
                    should_save = True
        else:
            should_save = True

        if should_save:
            super().save()

    def load(self):
        super().load()
        self.relay_board_list = []
        for device in self.config:
            self.relay_board_list.append(device['id'])
        self.update()

    def _run(self):
        self.scan_thread_event = threading.Event()

        buf = []
        while not self.scan_thread_event.is_set():
            try:
                if not len(buf):
                    logging.debug("... ... sending discovery message for relay boards")
                    self.discovery_socket.sendto(DISCOVERY_MESSAGE, DESTINATION_ADDRESS)
                    self.scan_thread_event.wait(1)
                (buf, address) = self.discovery_socket.recvfrom(30303)
                logging.debug(f"... received from {address}: {buf}")
                if "ETH008" in str(buf):
                    if not address[0] in self.relay_board_list:
                        logging.info(f"... ... found new module[{address[0]}]")
                        self.relay_board_list.append(address[0])
                        self.last_update = -1
                        continue
                else:
                    logging.debug(f"ignore unknown device [{buf}] with [{address}]")
                self.scan_thread_event.wait(1)
            except (socket.timeout, OSError):
                buf = []
                self.scan_thread_event.wait(TIMEOUT_UPDATE_AVAILABILITY)

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
            self.mqtt_client.publish(
                f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{str(ip).replace('.', '_')}/online",
                'true')
            for line in content.splitlines():
                if "relay" in line:
                    status = line[line.index(">") + 1:line.index("</")]
                    if status == "1" or status == "0":
                        status_list.append(status)
                    else:
                        status_list.append(STATE_UNKNOWN)
                        logging.warning("... ... WARN: state [%s] unknown" % status)

        except ConnectionError:
            logging.error(f"could not read status from relay board [{ip}]")
            self.last_update = -1
            self.mqtt_client.publish(
                f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{str(ip).replace('.', '_')}/online",
                'false')
        finally:
            return status_list

    def _set_status(self, ip, relay, state, toggle: bool = False):
        auth = (RELAY_USERNAME, RELAY_PASSWORD)

        url = "http://" + str(ip) + "/io.cgi?"
        url += "DOA" if state == b'1' or str(state) == "1" else "DOI"
        url += relay
        if toggle:
            url += '=30'  # + str(int(toggle) * 10)
        try:
            requests.get(url, auth=auth, timeout=1)
        except ConnectionError:
            logging.error(f"could not set value on relay board [{ip}]")
            self.last_update = -1
            self.mqtt_client.publish(
                f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{str(ip).replace('.', '_')}/online",
                'false')

    def announce_device(self, device):
        string_id = device['id'].replace('.', '_')
        device_name = f"Relay Board ({device['id']})"
        service_specific_command_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/+/command"
        logging.info(f"... ... subscribe to channel [{service_specific_command_topic}]")
        self.mqtt_client.subscribe(service_specific_command_topic, QOS)

        logging.info("... ... announce relay board with all actors and sensors [%s]",
                     device['state'])
        availability_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/online"

        for relay_id in device['state']:
            relay_name = "Relay {}-{}".format(string_id, relay_id)
            state_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/{relay_id}"
            unique_id = f"{string_id}-light-{relay_id}"
            config_topic = f"{MQTT_HOMEASSISTANT_PREFIX}/{MQTT_LIGHT}/{string_id}-{relay_id}/config"

            payload = PAYLOAD_SWITCH_ACTOR
            payload[MQTT_NAME] = relay_name
            payload[MQTT_COMMAND_TOPIC] = state_topic + "/command"
            payload[MQTT_STATE_TOPIC] = state_topic
            payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
            payload[MQTT_UNIQUE_ID] = unique_id
            payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = device[
                'id']  # f"{self.execution_mode}-{string_id}"
            payload[MQTT_DEVICE][MQTT_NAME] = device_name
            payload[MQTT_DEVICE][MQTT_DEVICE_DESCRIPTION] = f"via Gateway ({self.ip_address})"

            self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)
