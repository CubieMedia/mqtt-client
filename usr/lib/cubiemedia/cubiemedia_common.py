#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import sys
import logging
import subprocess
import netifaces as net

# interfaces / devices #
INTERFACES_WLAN = ['wlan0', 'wlp3s0']
INTERFACES_NETWORK = ['eth0', 'enp5s0']
ENOCEAN_PORT = "/dev/ttyAMA0"

# wording #
CUBIE_IO = "io"
CUBIE_ENOCEAN = "enocean"
CUBIE_RELAY = "relay"
CUBIE_RESET = "reset"
CUBIE_ANNOUNCE = "announce"
CUBIEMEDIA = "cubiemedia/"
STATE_UNKNOWN = 'unknown'

# MQTT #
QOS = 2
CUBIE_MQTT_SERVER = "homeassistant"
CUBIE_MQTT_USERNAME = "mqtt"
CUBIE_MQTT_PASSWORD = "autoInstall"
CUBIE_LEARN_MODE = True
CUBIE_TOPIC_COMMAND = CUBIEMEDIA + "command"
CUBIE_TOPIC_ANNOUNCE = CUBIEMEDIA + CUBIE_ANNOUNCE

# Relayboard #
RELAY_BOARD = "RELAYBOARD"
RELAY_USERNAME = 'admin'
RELAY_PASSWORD = 'password'


def get_ip_address():
    ip = get_ip_address_of_interface(INTERFACES_NETWORK)
    if ip is None:
        ip = get_ip_address_of_interface(INTERFACES_WLAN)
    if ip is None:
        print("... no device found that could have an IP Address...")
        logging.warning("... no device found that could have an IP Address...")

    #    print("... found IP [%s]" % ip)
    #    logging.info("... found IP [%s]" % ip)
    return ip


def get_ip_address_of_interface(interfaces):
    for interface in interfaces:
        if interface in net.interfaces():
            if len(net.ifaddresses(interface)) > 1 and len(net.ifaddresses(interface)[2]) > 0:
                return net.ifaddresses(interface)[2][0]['addr']

    return None


def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])