#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import logging
import subprocess
import sys


def exit_gracefully(system, *args):
    logging.info("... shutdown process")
    system.RUN = False

    system.shutdown()
    logging.info('... stopping MQTT Client...')
    system.mqtt_client.disconnect()


def install_package(package):
    subprocess.check_call(["python3", "-m", "pip", "install", package])

