#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging
import time
import sys

import netifaces as net

INTERFACES_WLAN = ['wlan0', 'wlp3s0']
INTERFACES_NETWORK = ['eth0', 'enp5s0']


def get_ip_address() -> str:
    ip = None
    while ip is None:
        ip = get_ip_address_of_interface(INTERFACES_NETWORK)
        if ip is None:
            ip = get_ip_address_of_interface(INTERFACES_WLAN)
        if ip is None or '169.' in ip:
            ip = None
            logging.warning("... no device found that could have an IP Address...")
            if 'unittest' in sys.modules.keys():
                logging.warning("... found test environment, using fake ip")
                return "192.168.103.43"
            else:
                time.sleep(3)
        else:
            logging.debug("... ... found IP [%s]" % ip)
            break
    return ip


def get_ip_address_of_interface(interfaces):
    try:
        for interface in interfaces:
            if interface in net.interfaces():
                if len(net.ifaddresses(interface)) > 1 and len(net.ifaddresses(interface)[2]) > 0:
                    return net.ifaddresses(interface)[2][0]['addr']
    except KeyError:
        pass

    return None
