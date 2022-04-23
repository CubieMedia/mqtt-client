#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import requests
import socket
import threading
import time

from cubiemedia_common import *

# Variables #

MQTT_SERVER = CUBIE_MQTT_SERVER
MQTT_USER = CUBIE_MQTT_USERNAME
MQTT_PASSWORD = CUBIE_MQTT_PASSWORD
MQTT_CLIENT = None
LEARN_MODE = CUBIE_LEARN_MODE
SEARCH_THREAD_EVENT = threading.Event()
UPDATE_TIMEOUT = 10
SEND_UPDATE_TIMEOUT = 30
KNOWN_DEVICE_LIST = []
MODULE_LIST = []
SUBSCRIPTION_LIST = []
LAST_UPDATE = time.time() - UPDATE_TIMEOUT + 3
SCAN_THREAD = threading.Thread()


def action(device):
    if not device['id'] in SUBSCRIPTION_LIST:
        print("... ... subscribing to [%s] for commands" % device['id'])
        logging.info("... ... subscribing to [%s] for commands" % device['id'])
        MQTT_CLIENT.subscribe(CUBIEMEDIA + device['id'].replace(".", "_") + "/+/command", 2)
        SUBSCRIPTION_LIST.append(device['id'])

    for known_device in KNOWN_DEVICE_LIST:
        if device['id'] == known_device['id']:
            for relay in device['state']:
                # print(f"device[{device['state'][relay]}] - known_device[{known_device['state'][relay]}]")
                if not device['state'][relay] == known_device['state'][relay]:
                    print("... ... action for [%s] Relay [%s] -> [%s]" % (device['id'], relay, device['state'][relay]))
                    logging.info(
                        "... ... action for [%s] Relay [%s] -> [%s]" % (device['id'], relay, device['state'][relay]))
                    MQTT_CLIENT.publish(CUBIEMEDIA + device['id'].replace(".", "_") + "/" + relay, device['state'][relay], 0,
                                   True)
                    known_device['state'][relay] = device['state'][relay]
            return True

    print("... ... unknown device, announce [%s]" % device['id'])
    logging.info("... ... unknown device, announce [%s]" % device['id'])
    MQTT_CLIENT.publish(CUBIE_TOPIC_ANNOUNCE, json.dumps(device))
    return False


def send(data):
    global LAST_UPDATE
    toggle = False
    for known_device in KNOWN_DEVICE_LIST:
        if data['ip'] == known_device['id']:
            if 'toggle' in known_device and int(data['id']) in known_device['toggle']:
                toggle = True
    print("... ... send data[%s] from HA with toggle[%s]" % (data, toggle))
    logging.debug("... ... send data[%s] from HA with toggle[%s]" % (data, toggle))
    set_status(data['ip'], data['id'], data['state'], toggle)
    LAST_UPDATE = -1 if toggle else 0


def update():
    global LAST_UPDATE
    data = {}
    if LAST_UPDATE < time.time() - UPDATE_TIMEOUT:
        relayboard_list = []
        send_data = False
        # print("... update data for all modules")
        for module in MODULE_LIST:
            known_device = None
            for temp_device in KNOWN_DEVICE_LIST:
                if module == temp_device['id']:
                    known_device = temp_device

            relayboard = {'id': str(module), 'type': RELAY_BOARD}
            status_list = read_status(module)
            relay_state_list = {}
            relay_state_changed_list = {}
            count = 1
            for status in status_list:
                relay_state_list[str(count)] = status
                if known_device is None or 'state' not in known_device or status != known_device['state'][
                    str(count)] or LAST_UPDATE < time.time() - SEND_UPDATE_TIMEOUT:
                    relay_state_changed_list[str(count)] = status
                    send_data = True
                count += 1

            if send_data:
                relayboard['state'] = relay_state_changed_list
                relayboard_list.append(relayboard)

        if send_data:
            data['devices'] = relayboard_list
        if LAST_UPDATE < 0:
            LAST_UPDATE = time.time() - int(UPDATE_TIMEOUT / 1.4)
        else:
            LAST_UPDATE = time.time()
    return data


def set_availability(state: bool):
    for device in KNOWN_DEVICE_LIST:
        MQTT_CLIENT.publish(CUBIEMEDIA + device['id'].replace(".", "_") + '/online', str(state).lower())


def init(client):
    global MQTT_CLIENT, SCAN_THREAD, SEARCH_THREAD_EVENT
    MQTT_CLIENT = client
    print("... starting scan thread")
    SCAN_THREAD = threading.Thread(target=scan_thread)
    SCAN_THREAD.daemon = True
    SCAN_THREAD.start()
    return load()


def shutdown():
    print('... set devices unavailable ...')
    logging.info('... set devices unavailable...')
    set_availability(False)

    print("... stopping scan thread")
    logging.info("... stopping scan thread")
    SEARCH_THREAD_EVENT.set()
    SCAN_THREAD.join()


def reset():
    global KNOWN_DEVICE_LIST
    KNOWN_DEVICE_LIST = []
    save()


def announce():
    for device in KNOWN_DEVICE_LIST:
        print("... ... announce device [%s]" % device['id'])
        logging.info("... ... announce device [%s]" % device['id'])
        MQTT_CLIENT.publish(CUBIE_TOPIC_ANNOUNCE, json.dumps(device))
        print("... ... subscribing to [%s] for commands" % device['id'])
        logging.info("... ... subscribing to [%s] for commands" % device['id'])
        MQTT_CLIENT.subscribe(CUBIEMEDIA + device['id'].replace(".", "_") + "/+/command", 2)
        if not device['id'] in SUBSCRIPTION_LIST:
            SUBSCRIPTION_LIST.append(device['id'])


def save(new_device=None):
    should_save = False
    if new_device is not None:
        if new_device['type'] == RELAY_BOARD and LEARN_MODE:
            add = True
            for known_device in KNOWN_DEVICE_LIST:
                if new_device['id'] == known_device['id']:
                    add = False
                    break
            if add:
                KNOWN_DEVICE_LIST.append(new_device)
                update()
                should_save = True
    else:
        should_save = True

    if should_save:
        with open('./relayList.json', 'w') as json_file:
            config = {'host': MQTT_SERVER, 'username': MQTT_USER, 'password': MQTT_PASSWORD, 'learn_mode': LEARN_MODE,
                      'deviceList': KNOWN_DEVICE_LIST}
            json.dump(config, json_file, indent=4, sort_keys=True)


def load():
    global KNOWN_DEVICE_LIST, MODULE_LIST, MQTT_SERVER, MQTT_USER, MQTT_PASSWORD, LEARN_MODE
    try:
        print("... loading devices")
        logging.info("... loading devices")
        with open('./relayList.json') as json_file:
            config = json.load(json_file)
            MQTT_SERVER = config['host']
            MQTT_USER = config['username']
            MQTT_PASSWORD = config['password']
            LEARN_MODE = config['learn_mode']
            KNOWN_DEVICE_LIST = config['deviceList']
        for device in KNOWN_DEVICE_LIST:
            MODULE_LIST.append(device['id'])
        update()
        return MQTT_SERVER, MQTT_USER, MQTT_PASSWORD
    except (IOError, ValueError):
        save()
        return load()


def delete(device):
    for known_device in KNOWN_DEVICE_LIST:
        print(f"{device['id']} - {known_device['id']}")
        if device['id'] == known_device['id']:
            KNOWN_DEVICE_LIST.remove(known_device)
            break


def scan_thread():
    global MODULE_LIST, SEARCH_THREAD_EVENT
    SEARCH_THREAD_EVENT = threading.Event()

    msg = "DISCOVER_RELAIS_MODULE"
    destination = ('<broadcast>', 30303)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(1)
    s.sendto(msg.encode(), destination)
    while not SEARCH_THREAD_EVENT.isSet():
        try:
            (buf, address) = s.recvfrom(30303)
            if not len(buf):
                break
            #      print("... received from %s: %s" %(address, buf))
            if "ETH008" in str(buf):
                if not address[0] in MODULE_LIST:
                    print(f"... found new module[{address[0]}]")
                    MODULE_LIST.append(address[0])
            continue
        except socket.timeout:
            pass

        SEARCH_THREAD_EVENT.wait(60)
        s.sendto(msg.encode(), destination)

    return True


def read_status(ip):
    status_list = []
    auth = (RELAY_USERNAME, RELAY_PASSWORD)

    url = "http://" + str(ip) + "/status.xml"
    try:
        r = requests.get(url, auth=auth, timeout=1)

        content = r.text
        #  print("... ... content: " + str(content))
        MQTT_CLIENT.publish(CUBIEMEDIA + str(ip).replace(".", "_") + '/online', 'true')
        for line in content.splitlines():
            if "relay" in line:
                status = line[line.index(">") + 1:line.index("</")]
                if status == "1" or status == "0":
                    status_list.append(status)
                else:
                    status_list.append(STATE_UNKNOWN)
                    logging.warning("... ... WARN: state [%s] unknown" % status)

    except ConnectionError:
        print(f"ERROR ... could not read status from relay board [{ip}]")
        logging.info(f"ERROR ... could not read status from relay board [{ip}]")
        MQTT_CLIENT.publish(CUBIEMEDIA + str(ip).replace(".", "_") + '/online', 'false')
    finally:
        return status_list


def set_status(ip, relay, state, toggle: bool = False):
    auth = (RELAY_USERNAME, RELAY_PASSWORD)

    url = "http://" + str(ip) + "/io.cgi?"
    url += "DOA" if state == b'1' or str(state) == "1" else "DOI"
    url += relay
    if toggle:
        url += '=30'  # + str(int(toggle) * 10)
    try:
        requests.get(url, auth=auth)
    except ConnectionError:
        print(f"ERROR ... could set value on relay board [{ip}]")
        logging.info(f"ERROR ... could not set value on relay board [{ip}]")


def set_learn_mode(enabled):
    global LEARN_MODE

    print(f"... set learn mode {enabled}")
    logging.info(f"... set learn mode {enabled}")

    LEARN_MODE = enabled
    save()
