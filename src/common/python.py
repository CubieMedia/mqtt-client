#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import json
import logging
import subprocess


def exit_gracefully(system, *args):
    logging.info("... shutdown process")
    system.RUN = False

    system.shutdown()
    logging.info('... stopping MQTT Client...')
    system.mqtt_client.disconnect()


def execute_command(command: []) -> str:
    return subprocess.check_output(command)


def get_configuration(config_name: str) -> {}:
    value = execute_command(["snapctl", "get", "-d", config_name]).strip()

    json_object = json.loads(value)
    if config_name in json_object:
        return json_object[config_name]
    else:
        return {}


def set_configuration(config_name: str, config: {}):
    execute_command(["snapctl", "set", f"{config_name}={json.dumps(config)}"])


def install_package(package):
    subprocess.check_call(["python3", "-m", "pip", "install", package])
