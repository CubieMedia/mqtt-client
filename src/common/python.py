#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import json
import logging
import subprocess
from subprocess import CalledProcessError


def exit_gracefully(system, *args):
    logging.info("... shutdown process")
    system.RUN = False

    system.shutdown()
    if system.mqtt_client:
        logging.info('... stopping MQTT Client...')
        system.mqtt_client.disconnect()


def execute_command(command: [], show_error=True) -> str:
    return subprocess.check_output(command, stderr=subprocess.DEVNULL)


def get_configuration(config_name: str) -> {}:
    value = []
    try:
        value = execute_command(["snapctl", "get", "-d", config_name]).strip()
        if len(value) < 3:
            value = execute_command(["snap", "get", "-d", "cubiemedia-mqtt-client", config_name]).strip()
    except CalledProcessError:
        try:
            value = execute_command(["snap", "get", "-d", "cubiemedia-mqtt-client", config_name]).strip()
        except CalledProcessError:
            logging.warning(
                "seems to be a non snap environment, could not load config [%s]\n"
                "Maybe try to login to Ubuntu with [snap login]" % config_name)
    json_object = json.loads(value)
    if config_name in json_object:
        return json_object[config_name]
    return []


def set_configuration(config_name: str, config: []):
    try:
        execute_command(["snapctl", "set", f"{config_name}={json.dumps(config)}"])
    except CalledProcessError:
        try:
            execute_command(["snap", "set", "cubiemedia-mqtt-client", f"{config_name}={json.dumps(config)}"])
        except CalledProcessError as e:
            logging.warning(
                "seems to be a non snap environment, could not save config [%s]\n"
                "Maybe try to login to Ubuntu with [snap login]" % config_name)
    return None


def install_package(package):
    subprocess.check_call(["python3", "-m", "pip", "install", package])
