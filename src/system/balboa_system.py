#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import logging
import socket
import threading
import time

from common import MQTT_CUBIEMEDIA, TIMEOUT_UPDATE_AVAILABILITY, CUBIE_TYPE, QOS, \
    MQTT_HOMEASSISTANT_PREFIX, CUBIE_BALBOA, TIMEOUT_UPDATE_SPA
from common.homeassistant import MQTT_NAME, MQTT_COMMAND_TOPIC, MQTT_STATE_TOPIC, \
    MQTT_AVAILABILITY_TOPIC, \
    MQTT_UNIQUE_ID, \
    MQTT_DEVICE, MQTT_DEVICE_IDS, MQTT_DEVICE_DESCRIPTION, PAYLOAD_SENSOR, MQTT_TEMPERATURE, \
    MQTT_UNIT, MQTT_STATE_CLASS, MQTT_DEVICE_CLASS, MQTT_MEASUREMENT, MQTT_SWITCH, MQTT_LIGHT, \
    MQTT_CONFIG_TOPIC, \
    MQTT_BINARY_SENSOR, MQTT_SENSOR, PAYLOAD_SPECIAL_SENSOR, MQTT_UNIT_OF_MEASUREMENT, \
    PAYLOAD_SWITCH_ACTOR, \
    MQTT_SUGGESTED_DISPLAY_PRECISION, MQTT_CLIMATE, PAYLOAD_SPA_ACTOR
from system.base_system import BaseSystem

VALID_PACKAGE_START = b'\xff\xaf\x13'

BALBOA_READ_BYTE = "balboa_read_byte"
BALBOA_WRITE_VALUE = "balboa_write_byte"
BALBOA_READ_FORMULA = "balboa_read_formula"
BALBOA_WRITE_FORMULA = "balboa_write_formula"

DISCOVERY_MESSAGE = "DISCOVER_RELAIS_MODULE".encode()
DESTINATION_ADDRESS = ('<broadcast>', 30303)

TEMPERATURE_RANGE_MAX = 40
TEMPERATURE_RANGE_MIN = 10


def is_light_enable(value) -> int:
    return 1 if value & 0x03 != 0 else 0


def is_jets_enable(value) -> int:
    return 1 if value & 0x03 == 2 else 0


def is_blower_enable(value) -> int:
    return 1 if value & 0x0c != 0 else 0


def is_heating_enable(value) -> str:
    return 'heating' if value & 0x30 != 0 else 'off'


def is_circulation_pump_enable(value) -> int:
    return 1 if value & 0x02 != 0 else 0


def get_operation_mode(value) -> str:
    return 'heat' if (value & 0x04 != 0) else 'off'


def correct_value(value):
    temperature = float(value) / 2
    if TEMPERATURE_RANGE_MIN <= temperature <= TEMPERATURE_RANGE_MAX:
        return temperature
    logging.warning(f"temperature value [{temperature}] out of range")
    return None


def send_toggle_message(value):
    # 0x04 - pump 1
    # 0x05 - pump 2
    # 0x0c - blower
    # 0x11 - light 1
    # 0x51 - heating mode
    # 0x50 - operation mode
    return b'\x0a\xbf\x11', bytes([value]) + b'\x00'


def send_temp_value(value):
    return b'\x0a\xbf\x20', bytes([value])


SERVICES = {
    "light": {
        MQTT_CONFIG_TOPIC: MQTT_LIGHT,
        BALBOA_READ_BYTE: 14,
        BALBOA_WRITE_VALUE: 0x11,
        BALBOA_READ_FORMULA: is_light_enable,
        BALBOA_WRITE_FORMULA: send_toggle_message
    },
    "jets": {
        MQTT_CONFIG_TOPIC: MQTT_SWITCH,
        BALBOA_READ_BYTE: 11,
        BALBOA_WRITE_VALUE: 0x04,
        BALBOA_READ_FORMULA: is_jets_enable,
        BALBOA_WRITE_FORMULA: send_toggle_message
    },
    "blower": {
        MQTT_CONFIG_TOPIC: MQTT_SWITCH,
        BALBOA_READ_BYTE: 13,
        BALBOA_WRITE_VALUE: 0x0c,
        BALBOA_READ_FORMULA: is_blower_enable,
        BALBOA_WRITE_FORMULA: send_toggle_message
    },
    "circulation_pump": {
        MQTT_CONFIG_TOPIC: MQTT_BINARY_SENSOR,
        BALBOA_READ_BYTE: 13,
        BALBOA_READ_FORMULA: is_circulation_pump_enable,
    },
    "heating": {
        MQTT_CONFIG_TOPIC: MQTT_BINARY_SENSOR,
        BALBOA_READ_BYTE: 10,
        BALBOA_READ_FORMULA: is_heating_enable,
    },
    "temperature_control": {
        MQTT_CONFIG_TOPIC: MQTT_CLIMATE,
        BALBOA_READ_BYTE: 10,
        BALBOA_WRITE_VALUE: 0x50,
        BALBOA_READ_FORMULA: get_operation_mode,
        BALBOA_WRITE_FORMULA: send_toggle_message,
    },
    "current_temperature": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        BALBOA_READ_BYTE: 2,
        MQTT_UNIT: "°C",
        MQTT_SUGGESTED_DISPLAY_PRECISION: 1,
        MQTT_STATE_CLASS: MQTT_MEASUREMENT,
        MQTT_DEVICE_CLASS: MQTT_TEMPERATURE,
        BALBOA_READ_FORMULA: correct_value
    },
    "target_temperature": {
        MQTT_CONFIG_TOPIC: MQTT_SENSOR,
        BALBOA_READ_BYTE: 20,
        MQTT_UNIT: "°C",
        MQTT_SUGGESTED_DISPLAY_PRECISION: 1,
        MQTT_STATE_CLASS: MQTT_MEASUREMENT,
        MQTT_DEVICE_CLASS: MQTT_TEMPERATURE,
        BALBOA_READ_FORMULA: correct_value,
        BALBOA_WRITE_FORMULA: send_temp_value,
    }
}


class BalboaSystem(BaseSystem):
    _spa_dict = {}
    _all_spas_scanned = False
    _index_of_current_spa = 0
    _scan_thread = threading.Thread()
    _scan_thread_event = threading.Event()
    _discovery_socket = None

    _error_message_shown = False

    def __init__(self):
        self.execution_mode = CUBIE_BALBOA
        super().__init__()

    def action(self, device: {}) -> bool:
        if {'id', 'state'}.issubset(device):
            for known_device in self.config:
                if device['id'] == known_device['id']:
                    for service, value in device['state'].items():
                        if service == 'temperature_control' and 'auto' in known_device['state'] and \
                                known_device['state']['auto']:
                            value = 'auto'

                        logging.info(f"... ... action for Spa [{device['id']}] with service [{service}] -> [{value}]")
                        self.mqtt_client.publish(
                            f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{device['id'].replace('.', '_')}/{service}",
                            value, True)
                    self.save()
                return True
        else:
            logging.warning(f"... received action with wrong data [{device}]")
        return False

    def send(self, data) -> bool:
        if {'ip', 'id', 'state'}.issubset(data) and data['id'] in SERVICES:
            service = data['id']
            attributes = SERVICES[service]
            new_state = data['state']
            spa_ip = data['ip']
            known_device = None
            for temp_device in self.config:
                if spa_ip == temp_device['id']:
                    known_device = temp_device
            if known_device:
                old_state = known_device['state'][service]
                if service == "temperature_control":
                    if new_state == 'auto':
                        known_device['state']['auto'] = True
                    elif known_device['state']['auto']:
                        known_device['state']['auto'] = False
                    self.last_update = 0
                logging.info(f"... send service [{service}] - old state[{old_state}] -> new state[{new_state}]")

                if new_state != old_state and 'auto' != new_state:
                    if BALBOA_WRITE_FORMULA in attributes:
                        if BALBOA_WRITE_VALUE in attributes:
                            msg_type, payload = attributes[BALBOA_WRITE_FORMULA](
                                attributes[BALBOA_WRITE_VALUE])
                        else:
                            msg_type, payload = attributes[BALBOA_WRITE_FORMULA](
                                int(float(data['state']) * 2))
                        length = 5 + len(payload)
                        checksum = compute_checksum(bytes([length]), msg_type + payload)
                        prefix = b'\x7e'
                        message = prefix + bytes([length]) + msg_type + payload + bytes(
                            [checksum]) + prefix

                        spa_socket = self._get_spa_socket(spa_ip)
                        try:
                            spa_socket.send(message)
                        except Exception as e:
                            logging.error(f"could not send message to spa [{data}]", e)
                        self._remove_socket(spa_ip)
                        self.last_update = 0
                    else:
                        logging.warning(
                            f"could not write value for data [{data}], no write schema defined")
                else:
                    logging.debug(f"state did not change or 'auto' mode [{data}], not sending data")
            else:
                logging.warning(f"unknown device [{data}]")
                return False
            return True

        return super().send(data)

    def update(self):
        data = {}

        if self.last_update < time.time() - TIMEOUT_UPDATE_SPA and len(self._spa_dict) > 0:
            for spa_ip, values in self._spa_dict.items():
                logging.info(f"... updating spa [{spa_ip}]")
                known_device = None
                for temp_device in self.config:
                    if spa_ip == temp_device['id']:
                        known_device = temp_device
                        break

                spa_json = {'id': str(spa_ip), CUBIE_TYPE: CUBIE_BALBOA,
                            'client_id': self.client_id,
                            'state': {}}
                if known_device:
                    try:
                        spa_socket = self._get_spa_socket(spa_ip)
                        len_chunk = spa_socket.recv(2)
                        if len_chunk == b'' or len(len_chunk) == 0:
                            return False
                        length = len_chunk[1]
                        if int(length) == 0:
                            return False
                        spa_data = spa_socket.recv(length)

                        if spa_data and spa_data[0:3] == VALID_PACKAGE_START:
                            spa_json['state'] = get_state_from(spa_data, known_device)

                        self.mqtt_client.publish(
                            f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{spa_ip.replace('.', '_')}/online", "true")
                        self._error_message_shown = False

                        data['devices'] = [spa_json]
                        self._remove_socket(spa_ip)
                    except Exception as e:
                        if not self._error_message_shown:
                            logging.error(
                                f"Connection to {spa_ip} not possible [{e}], is something else connected to your Spa?")
                            self._error_message_shown = True
                        self.mqtt_client.publish(
                            f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{spa_ip.replace('.', '_')}/online", "false")

                else:
                    self.save(spa_json)
                    self.announce()

                if self.last_update < 0:
                    self.last_update = time.time() - int(TIMEOUT_UPDATE_SPA * 0.99)
                else:
                    self.last_update = time.time()

        return data

    def set_availability(self, state: bool):
        super().set_availability(state)
        for device in self.config:
            self.mqtt_client.publish(
                f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{device['id'].replace('.', '_')}/online",
                str(state).lower())

    def init(self):
        self.last_update = time.time() - int(TIMEOUT_UPDATE_SPA * 0.98)
        super().init()

        socket.setdefaulttimeout(5)
        self._discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._discovery_socket.settimeout(3)

        logging.info("... starting scan thread")
        self._scan_thread = threading.Thread(target=self._run)
        self._scan_thread.daemon = True
        self._scan_thread.start()

    def shutdown(self):
        logging.info('... set devices unavailable...')
        self.set_availability(False)

        if self._scan_thread.is_alive():
            logging.info("... stopping scan thread...")
            self._scan_thread_event.set()
            self._scan_thread.join()

        super().shutdown()

    def announce(self):
        super().announce()
        for device in self.config:
            self._announce_device(device)

    def save(self, device=None):
        should_save = False
        if device:
            if device[CUBIE_TYPE] == CUBIE_BALBOA and self.system_config['devices_can_be_added']:
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
        self._spa_dict = {}
        for device in self.config:
            self._spa_dict[device['id']] = {}
        self.update()

    def _run(self):
        self._scan_thread_event = threading.Event()

        buf = []
        while not self._scan_thread_event.is_set():
            try:
                if not len(buf):
                    logging.debug("... ... sending discovery message for relay boards")
                    self._discovery_socket.sendto(DISCOVERY_MESSAGE, DESTINATION_ADDRESS)
                    self._scan_thread_event.wait(1)
                (buf, address) = self._discovery_socket.recvfrom(30303)
                logging.debug(f"... received from {address}: {buf}")
                if "BWGSPA" in str(buf):
                    if not address[0] in self._spa_dict:
                        logging.info(f"... ... found new spa [{address[0]}]")
                        self._spa_dict[address[0]] = {}
                        self.last_update = -1
                        continue
                else:
                    logging.debug(f"ignore unknown device [{buf}] with [{address}]")
                self._scan_thread_event.wait(1)
            except (socket.timeout, OSError):
                buf = []
                self._scan_thread_event.wait(TIMEOUT_UPDATE_AVAILABILITY)

        self._discovery_socket.close()
        return True

    def _get_spa_socket(self, spa_ip) -> socket.socket:
        if spa_ip in self._spa_dict:
            spa_socket = self._spa_dict[spa_ip]['socket'] if 'socket' in self._spa_dict[
                spa_ip] else None
            if spa_socket:
                logging.debug(f"... ... reuse socket for spa [{self._spa_dict[spa_ip]}]")
                return spa_socket
            else:
                logging.debug(f"... ... creating new socket for spa [{spa_ip}]")
                spa_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                spa_socket.connect((spa_ip, 4257))
                self._spa_dict[spa_ip]['socket'] = spa_socket
                if 'socket_count' in self._spa_dict[spa_ip]:
                    self._spa_dict[spa_ip]['socket_count'] += 1
                else:
                    self._spa_dict[spa_ip]['socket_count'] = 1

                return spa_socket
        raise ValueError(f"Could not find Spa [{spa_ip}]")

    def _remove_socket(self, spa_ip):
        if spa_ip in self._spa_dict:
            if 'socket_count' in self._spa_dict[spa_ip]:
                self._spa_dict[spa_ip]['socket_count'] -= 1
            else:
                self._spa_dict[spa_ip]['socket_count'] = 0

            if self._spa_dict[spa_ip]['socket_count'] <= 0:
                spa_socket = self._spa_dict[spa_ip]['socket'] if 'socket' in self._spa_dict[spa_ip] else None
                if spa_socket:
                    logging.debug(f"... ... closing socket for spa [{spa_ip}]")
                    del self._spa_dict[spa_ip]['socket']
                    spa_socket.close()

    def _announce_device(self, device):
        string_id = device['id'].replace('.', '_')
        device_name = f"Balboa Spa ({device['id']})"
        service_specific_command_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/+/command"
        logging.info(f"... ... subscribe to channel [{service_specific_command_topic}]")
        self.mqtt_client.subscribe(service_specific_command_topic, QOS)

        logging.info("... ... announce spa [%s] with all actors and sensors", device['id'])
        availability_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/online"

        for service, attributes in SERVICES.items():
            state_topic = f"{MQTT_CUBIEMEDIA}/{self.execution_mode}/{string_id}/{service}"
            unique_id = f"spa-{string_id}-{service}"
            config_topic = f"{MQTT_HOMEASSISTANT_PREFIX}/{attributes[MQTT_CONFIG_TOPIC]}/spa-{string_id}-{service}/config"

            if attributes[MQTT_CONFIG_TOPIC] == MQTT_SENSOR:
                payload = PAYLOAD_SPECIAL_SENSOR
                payload[MQTT_SUGGESTED_DISPLAY_PRECISION] = attributes[
                    MQTT_SUGGESTED_DISPLAY_PRECISION]
                payload[MQTT_UNIT_OF_MEASUREMENT] = attributes[MQTT_UNIT]
                payload[MQTT_STATE_CLASS] = attributes[MQTT_STATE_CLASS]
                payload[MQTT_DEVICE_CLASS] = attributes[MQTT_DEVICE_CLASS]
            elif attributes[MQTT_CONFIG_TOPIC] == MQTT_BINARY_SENSOR:
                payload = PAYLOAD_SENSOR
            elif attributes[MQTT_CONFIG_TOPIC] == MQTT_CLIMATE:
                payload = PAYLOAD_SPA_ACTOR
                payload[MQTT_COMMAND_TOPIC] = state_topic + "/command"
            else:
                payload = PAYLOAD_SWITCH_ACTOR
                payload[MQTT_COMMAND_TOPIC] = state_topic + "/command"

            payload[MQTT_NAME] = service.replace('_', ' ').title()
            payload[MQTT_STATE_TOPIC] = state_topic
            payload[MQTT_AVAILABILITY_TOPIC] = availability_topic
            payload[MQTT_UNIQUE_ID] = unique_id
            payload[MQTT_DEVICE][MQTT_DEVICE_IDS] = device[
                'id']  # f"{self.execution_mode}-{string_id}"
            payload[MQTT_DEVICE][MQTT_NAME] = device_name
            payload[MQTT_DEVICE][MQTT_DEVICE_DESCRIPTION] = f"via Gateway ({self.ip_address})"

            self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)

    # unused still needed for documentation
    def _handle_status_update(self, byte_array):
        if 0x50 >= byte_array[2] >= 0x14:
            self._current_temp = byte_array[2]
        else:
            # _LOGGER.warning(f"value out of range {byte_array[2]}")
            return
        self._priming = byte_array[1] & 0x01 == 1

        self._hour = byte_array[3]
        self._minute = byte_array[4]
        self._heating_mode = \
            ("Ready", "Rest", "Ready in Rest")[byte_array[5]]
        time_scale = byte_array[9]
        self._temp_scale = "°F" if (time_scale & 0x01 == 0) else "°C"
        self._time_scale = "12 Hr" if (time_scale & 0x02 == 0) else "24 Hr"
        self._heating = byte_array[10] & 0x30 != 0
        self._temp_range = "eco" if (byte_array[10] & 0x04 == 0) else "performance"
        pump_status = byte_array[11]
        self._pump1 = ("Off", "Low", "High")[pump_status & 0x03]
        self._pump2 = ("Off", "Low", "High")[pump_status & 0x12]
        self._circulation_pump = byte_array[13] & 0x02 != 0
        self._light = byte_array[14] & 0x03 != 0
        self._target_temp = byte_array[20]


def get_state_from(chunk, known_device):
    response = chunk[3:]
    service_json = {}
    for service, attributes in SERVICES.items():
        formula = attributes[BALBOA_READ_FORMULA]
        data_byte = response[attributes[BALBOA_READ_BYTE]]
        value = formula(data_byte)
        if value is None:
            value = known_device['state'][service]
        if (service not in known_device['state'] or value != known_device['state'][service]
                or service == 'temperature_control'):
            service_json[service] = value
            known_device['state'][service] = value
    return service_json


def compute_checksum(len_bytes, data):
    import crc8
    hash_value = crc8.crc8()
    hash_value._sum = 0x02
    hash_value.update(len_bytes)
    hash_value.update(data)
    checksum = hash_value.digest()[0]
    checksum = checksum ^ 0x02
    return checksum
