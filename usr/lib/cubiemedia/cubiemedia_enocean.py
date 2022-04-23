#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import copy
import json
import time
from threading import Timer

from enocean.communicators.serialcommunicator import SerialCommunicator
from enocean.protocol.constants import PACKET, RORG
from serial import SerialException

from cubiemedia_common import *

try:
    import queue
except ImportError:
    print("WARN: queue not found, trying Queue")
    import Queue as queue

# Variables #

try:
    COMMUNICATOR = SerialCommunicator(ENOCEAN_PORT)
except SerialException:
    print("... WARNING ... could not initialise serial communication, running in development mode?")
    logging.info("... WARNING ... could not initialise serial communication, running in development mode?")
    COMMUNICATOR = None
MQTT_SERVER = CUBIE_MQTT_SERVER
MQTT_USER = CUBIE_MQTT_USERNAME
MQTT_PASSWORD = CUBIE_MQTT_PASSWORD
MQTT_CLIENT = None
UPDATE_TIMEOUT = 30
LAST_UPDATE = time.time()
LEARN_MODE = CUBIE_LEARN_MODE
KNOWN_DEVICE_LIST = []
TIMERS = {}


def action(device):
    should_save = False
    client_id = MQTT_CLIENT._client_id.decode()

    for known_device in KNOWN_DEVICE_LIST:
        if str(device['id']).upper() == str(known_device['id']).upper():
            if known_device['client_id'] != client_id:
                # device is not managed by this gateway
                if device['dbm'] > known_device['dbm']:
                    device['client_id'] = client_id
                    print("... ... device with better connection, announce [%s]" % device)
                    logging.info("... ... device with better connection, announce [%s]" % device)
                    MQTT_CLIENT.publish(CUBIE_TOPIC_ANNOUNCE, json.dumps(device))
                    return False
                return True
            if str(device['type']).upper() == "RPS":
                for topic in device['state']:
                    if 'state' not in known_device or len(known_device['state']) == 0 or (
                            topic in known_device['state'] and device['state'][topic] != known_device['state'][topic]):
                        channel_topic = CUBIEMEDIA + str(device['id']).lower() + '/' + topic
                        value = device['state'][topic]
                        if value == 1:
                            create_timer_for(channel_topic)
                        else:
                            print("... ... action for [%s]" % channel_topic)
                            logging.info("... ... action for [%s]" % channel_topic)
                            if channel_topic in TIMERS and TIMERS[channel_topic] is not True:
                                MQTT_CLIENT.publish(channel_topic, 1, 0, True)
                                timer = TIMERS[channel_topic]
                                timer.cancel()
                                del TIMERS[channel_topic]
                                short_press_timer = Timer(0.5, MQTT_CLIENT.publish, [channel_topic, 0, 0, True])
                                short_press_timer.start()
                            else:
                                if channel_topic in TIMERS:
                                    del TIMERS[channel_topic]
                                MQTT_CLIENT.publish(channel_topic + "/longpush", 0, 0, True)
                        should_save = True
                known_device['state'] = device['state']
                if device['dbm'] > known_device['dbm']:
                    known_device['dbm'] = device['dbm']
                if should_save:
                    save()
            else:
                print("... ... send message for [%s]" % device['id'])
                MQTT_CLIENT.publish('cubiemedia/' + str(device['id']).lower(), json.dumps(device['state']))
            return True

    device['client_id'] = client_id
    print("... ... unknown device, announce [%s]" % device)
    logging.info("... ... unknown device, announce [%s]" % device)
    MQTT_CLIENT.publish(CUBIE_TOPIC_ANNOUNCE, json.dumps(device))
    return False


def create_timer_for(channel_topic, force=False):
    if channel_topic not in TIMERS:
        timer = Timer(0.8, longpress_timer, [channel_topic])
        TIMERS[channel_topic] = timer
        timer.start()
    elif force:
        print("... ... sending longpush [%s]" % channel_topic)
        logging.info("... ... sending longpush [%s]" % channel_topic)
        MQTT_CLIENT.publish(channel_topic + "/longpush", 1, 0, True)


def longpress_timer(channel_topic):
    TIMERS[channel_topic] = True
    print("... ... sending longpush [%s]" % channel_topic)
    logging.info("... ... sending longpush [%s]" % channel_topic)
    MQTT_CLIENT.publish(channel_topic + "/longpush", 1, 0, True)

    topic_array = channel_topic.split('/')
    device_id = topic_array[1]
    button = topic_array[2]
    device = None
    for known_device in KNOWN_DEVICE_LIST:
        if device_id == known_device['id']:
            device = known_device
            break

    if device is not None and 'channel_config' in device:
        channel_config = device['channel_config']
        print("... ... ... found config[%s] for device[%s] and button[%s]" % (channel_config, device_id, button))
        if button[0] in channel_config:
            device_topic = channel_config[button[0]]
            if 'dimmer' in device_topic:
                value = 5 if button[1] == '1' else 95
                while channel_topic in TIMERS:
                    MQTT_CLIENT.publish(device_topic, '{"turn": "on","brightness": ' + str(value))
                    value += 10 if button[1] == '1' else -10
                    time.sleep(0.5)
            else:
                print("WARN: unknown device[%s]" % device_topic)


def set_availability(state: bool):
    for device in KNOWN_DEVICE_LIST:
        if device['client_id'] == MQTT_CLIENT._client_id.decode():
            MQTT_CLIENT.publish(CUBIEMEDIA + str(device['id']).lower() + '/online', str(state).lower())


def send(data):
    raise NotImplemented(f"sending data[{data}] is not implemented")


def update():
    global COMMUNICATOR, LAST_UPDATE, UPDATE_TIMEOUT
    data = {}

    try:
        packet = COMMUNICATOR.receive.get(block=False, timeout=1)
        if packet.packet_type == PACKET.RADIO_ERP1:
            sensor = {'id': packet.sender_hex.replace(':', '').lower()}
            if packet.rorg == RORG.RPS:
                sensor['type'] = 'RPS'
                sensor['dbm'] = packet.dBm
                sensor['state'] = get_rps_state_from(packet)
                data['devices'] = [sensor]
            else:
                logging.error(f"device type (RORG: {packet.rorg}) not supported")
    except queue.Empty:
        pass
    except Exception as e:
        logging.error("ERROR: %s" % e)

    if LAST_UPDATE < time.time() - UPDATE_TIMEOUT:
        set_availability(True)
        LAST_UPDATE = time.time()
    return data


def get_rps_state_from(packet):
    state = {}
    data = packet.data[1]
    sa = data & 0x40 >> 6
    button_action = data & 0xE0
    energy_bow = (data & 0x10) >> 4

    # print("SA: %s, Action: %02X, EB: %s" % (sa, button_action, energy_bow))
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


def init(client):
    global COMMUNICATOR, MQTT_CLIENT
    MQTT_CLIENT = client
    if COMMUNICATOR:
        print("... starting serial communicator")
        logging.info("... starting serial communicator")
        COMMUNICATOR.start()
        time.sleep(0.100)
    return load()


def shutdown():
    global COMMUNICATOR
    print('... set devices unavailable ...')
    logging.info('... set devices unavailable...')
    set_availability(False)

    if COMMUNICATOR:
        print('... stopping Enocean Communicator...')
        COMMUNICATOR.stop()
        time.sleep(1)


def reset():
    global KNOWN_DEVICE_LIST
    KNOWN_DEVICE_LIST = []
    save()


def announce():
    global LAST_UPDATE
    for device in KNOWN_DEVICE_LIST:
        if device['client_id'] == MQTT_CLIENT._client_id.decode():
            print("... ... announce device [%s]" % device['id'])
            logging.info("... ... announce device [%s]" % device['id'])
            MQTT_CLIENT.publish(CUBIE_TOPIC_ANNOUNCE, json.dumps(device))
            for topic in device['state']:
                if device['state'][topic] == 1:
                    channel_topic = CUBIEMEDIA + str(device['id']).lower() + '/' + topic
                    create_timer_for(channel_topic, True)
    LAST_UPDATE = 0


def save(new_device=None):
    should_save = False
    device = None
    if new_device is not None:
        if (str(new_device['type']).upper() == "RPS" or str(new_device['type']).upper() == "TEMP") and LEARN_MODE:
            add = True
            for known_device in KNOWN_DEVICE_LIST:
                if str(new_device['id']).upper() == str(known_device['id']).upper():
                    add = False
                    if new_device['dbm'] > known_device['dbm']:
                        device = copy.copy(new_device)
                        del new_device['state']
                        print("... ... replace device[%s]" % new_device)
                        logging.info("... ... replace device[%s]" % new_device)
                        KNOWN_DEVICE_LIST[KNOWN_DEVICE_LIST.index(known_device)] = new_device
                        should_save = True
                    break

            if add:
                device = copy.copy(new_device)
                if 'state' in new_device:
                    del new_device['state']
                print("... ... adding new device[%s]" % new_device['id'])
                KNOWN_DEVICE_LIST.append(new_device)
                should_save = True
    else:
        should_save = True

    if should_save:
        with open('./deviceList.json', 'w') as json_file:
            config = {'host': MQTT_SERVER, 'username': MQTT_USER, 'password': MQTT_PASSWORD, 'learn_mode': LEARN_MODE,
                      'deviceList': KNOWN_DEVICE_LIST}
            json.dump(config, json_file, indent=4, sort_keys=True)

    if device is not None:
        action(device)


def load():
    global KNOWN_DEVICE_LIST, MQTT_SERVER, MQTT_USER, MQTT_PASSWORD, LEARN_MODE
    try:
        print("... loading devices")
        logging.info("... loading devices")
        with open('./deviceList.json') as json_file:
            config = json.load(json_file)
            MQTT_SERVER = config['host']
            MQTT_USER = config['username']
            MQTT_PASSWORD = config['password']
            LEARN_MODE = config['learn_mode']
            KNOWN_DEVICE_LIST = config['deviceList']
            return MQTT_SERVER, MQTT_USER, MQTT_PASSWORD
    except IOError:
        save()
        return load()


def delete(device):
    for known_device in KNOWN_DEVICE_LIST:
        if str(device['id']).upper() == str(known_device['id']).upper():
            KNOWN_DEVICE_LIST.remove(known_device)
            break
    save()

    print(f"... deleted device {device}")
    logging.info(f"... deleted device {device}")


def set_learn_mode(enabled):
    global LEARN_MODE

    print(f"... set learn mode {enabled}")
    logging.info(f"... set learn mode {enabled}")

    LEARN_MODE = enabled
    save()
