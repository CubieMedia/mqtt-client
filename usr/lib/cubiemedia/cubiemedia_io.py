#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import os
import sys
import time
import json

from cubiemedia_common import install_package

if os.environ.get('SNAP_ARCH') == 'armhf':
    try:
        import RPi.GPIO as GPIO
    except (ModuleNotFoundError, RuntimeError) as e:
        install_package("RPi.GPIO")
        import RPi.GPIO as GPIO
else:
    print("... demo mode [can not load GPIO module]")
    GPIO = None

sys.path.append('/usr/lib/cubiemedia/')
sys.path.append('../lib/cubiemedia/')

from cubiemedia_common import *

# Variables #

IP_ADDRESS = get_ip_address()
MQTT_SERVER = CUBIE_MQTT_SERVER
MQTT_USER = CUBIE_MQTT_USERNAME
MQTT_PASSWORD = CUBIE_MQTT_PASSWORD
MQTT_CLIENT = None
UPDATE_TIMEOUT = 30
LAST_UPDATE = time.time()
LEARN_MODE = CUBIE_LEARN_MODE
KNOWN_DEVICE_LIST = []


def action(device):
    print("... ... action for [%s]" % device)
    logging.info("... ... action for [%s]" % device)
    MQTT_CLIENT.publish('cubiemedia/' + device['ip'].replace(".", "_") + "/" + str(device['id']),
                        json.dumps(device['value']), 0, True)


def send(data):
    print("... ... send data[%s] from HA" % data)
    logging.info("... ... send data[%s] from HA" % data)
    if GPIO:
        GPIO.output(int(data['id']), GPIO.LOW if int(data['state']) == 1 else GPIO.HIGH)


def update():
    global LAST_UPDATE, UPDATE_TIMEOUT
    data = {}

    device_list = []
    if GPIO:
        for device in KNOWN_DEVICE_LIST:
            if device['function'] == "IN":
                value = GPIO.input(device['id'])
            elif device['function'] == "OUT":
                value = 1 if GPIO.input(device['id']) == 0 else 0
            else:
                print("WARN: could not find valid function for device[%s] on update" % device)
                continue

            if value != device['value']:
                # print("%s value %s" % (device['id'], value))
                device['value'] = value
                device['ip'] = IP_ADDRESS
                device_list.append(device)

    data['devices'] = device_list

    if LAST_UPDATE < time.time() - UPDATE_TIMEOUT:
        set_availability(True)
        LAST_UPDATE = time.time()
    return data


def announce():
    device = {'id': IP_ADDRESS, 'type': "GPIO"}
    for gpio in KNOWN_DEVICE_LIST:
        device['config'] = gpio
        print("... ... announce gpio device [%s]" % device)
        logging.info("... ... announce gpio device [%s]" % device)
        MQTT_CLIENT.publish(CUBIE_TOPIC_ANNOUNCE, json.dumps(device))

    topic = CUBIEMEDIA + IP_ADDRESS.replace(".", "_") + "/+/command"
    print("... ... subscribing to [%s] for gpio output commands" % topic)
    logging.info("... ... subscribing to [%s] for gpio output commands" % topic)
    MQTT_CLIENT.subscribe(topic, 2)
    set_availability(True)


def set_availability(state: bool):
    MQTT_CLIENT.publish(CUBIEMEDIA + IP_ADDRESS.replace(".", "_") + '/online', str(state).lower())


def save(new_device=None, client=None):
    global KNOWN_DEVICE_LIST, LEARN_MODE
    if new_device is None:
        if KNOWN_DEVICE_LIST is None or len(KNOWN_DEVICE_LIST) == 0:
            KNOWN_DEVICE_LIST = [{'id': 7, 'function': "IN", 'type': "GPIO", 'value': 0},
                                 {'id': 11, 'function': "IN", 'type': "GPIO", 'value': 0},
                                 {'id': 13, 'function': "IN", 'type': "GPIO", 'value': 0},
                                 {'id': 15, 'function': "IN", 'type': "GPIO", 'value': 0},
                                 {'id': 12, 'function': "OUT", 'type': "GPIO", 'value': 0},
                                 {'id': 16, 'function': "OUT", 'type': "GPIO", 'value': 0},
                                 {'id': 18, 'function': "OUT", 'type': "GPIO", 'value': 0},
                                 {'id': 22, 'function': "OUT", 'type': "GPIO", 'value': 0}]

        with open('./gpioList.json', 'w') as json_file:
            config = {'host': CUBIE_MQTT_SERVER, 'username': CUBIE_MQTT_USERNAME, 'password': CUBIE_MQTT_PASSWORD,
                      'learn_mode': LEARN_MODE, 'deviceList': KNOWN_DEVICE_LIST}
            json.dump(config, json_file, indent=4, sort_keys=True)


def load():
    global KNOWN_DEVICE_LIST, MQTT_SERVER, MQTT_USER, MQTT_PASSWORD, LEARN_MODE
    try:
        print("... loading devices")
        logging.info("... loading devices")
        with open('./gpioList.json') as json_file:
            config = json.load(json_file)
            MQTT_SERVER = config['host']
            MQTT_USER = config['username']
            MQTT_PASSWORD = config['password']
            LEARN_MODE = config['learn_mode']
            KNOWN_DEVICE_LIST = config['deviceList']
            return MQTT_SERVER, MQTT_USER, MQTT_PASSWORD
    except (IOError, ValueError):
        save()
        return load()


def delete(device):
    print("... delete not supported for IO devices, please change config locally")
    logging.info("... delete not supported for IO devices, please change config locally")


def init(client):
    global MQTT_CLIENT
    MQTT_CLIENT = client
    server, user, password = load()
    if GPIO:
        GPIO.setmode(GPIO.BOARD)
        # GPIO.setmode(GPIO.BCM)
        for device in KNOWN_DEVICE_LIST:
            if device['function'] == "IN":
                print("... set Pin %d as INPUT" % device['id'])
                logging.info("... set Pin %d as INPUT" % device['id'])
                GPIO.setup(device['id'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            elif device['function'] == "OUT":
                print("... set Pin %d as OUTPUT" % device['id'])
                logging.info("... set Pin %d as OUTPUT" % device['id'])
                GPIO.setup(device['id'], GPIO.OUT)
                GPIO.output(device['id'], GPIO.HIGH)
            else:
                print("WARN: could not find valid function for device[%s] on init" % device)
    return server, user, password


def reset():
    global KNOWN_DEVICE_LIST
    KNOWN_DEVICE_LIST = []
    save()


def shutdown():
    print('... set devices unavailable ...')
    logging.info('... set devices unavailable...')
    set_availability(False)

    print('... cleanup GPIO Pins...')
    logging.info('... cleanup GPIO Pins...')
    if GPIO and len(KNOWN_DEVICE_LIST) > 0:
        GPIO.cleanup()


def set_learn_mode(enabled):
    global LEARN_MODE

    print(f"... set learn mode {enabled}")
    logging.info(f"... set learn mode {enabled}")

    LEARN_MODE = enabled
    save()
