#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging
import sys

import ifaddr


def get_ip_address() -> str:
    ip_list = []

    if 'unittest' in sys.modules.keys():
        logging.warning("... found test environment, using fake ip")
        return "192.168.123.45"

    adapters = ifaddr.get_adapters()
    for adapter in adapters:
        logging.debug("... found network adapter %s", adapter.nice_name)
        for ip in adapter.ips:
            logging.debug("... ... %s/%s" % (ip.ip, ip.network_prefix))
            ip_list.append(ip.ip)

    if len(ip_list) > 0:
        for ip in ip_list:
            if ip and not ip.startswith('169') and not ip.startswith('127'):
                logging.debug("... found IP [%s]" % ip)
                return ip
    else:
        logging.warning("... no device found that could have an IP Address...")
    return None
