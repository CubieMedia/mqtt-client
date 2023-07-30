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
    logging.info('... stopping MQTT Client...')
    system.mqtt_client.disconnect()


def execute_command(command: []) -> str:
    return subprocess.check_output(command)


def get_configuration(config_name: str) -> {}:
    try:
        value = execute_command(["snapctl", "get", "-d", config_name]).strip()

        json_object = json.loads(value)
        if config_name in json_object:
            return json_object[config_name]
    except FileNotFoundError:
        logging.warning("seems to be a non snap environment, could not load config [%s]" % config_name)
    return None


def set_configuration(config_name: str, config: {}):
    try:
        execute_command(["snapctl", "set", f"{config_name}={json.dumps(config)}"])
    except CalledProcessError:
        logging.warning("seems to be a non snap environment, could not save config")
    return None


def install_package(package):
    subprocess.check_call(["python3", "-m", "pip", "install", package])
