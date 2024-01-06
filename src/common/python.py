#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import json
import logging
import subprocess

from common import COLOR_YELLOW, COLOR_DEFAULT


def exit_gracefully(system, *args):
    logging.info("... shutdown process")
    system.RUN = False

    system.shutdown()
    if system.mqtt_client:
        logging.info('... stopping MQTT Client...')
        system.mqtt_client.disconnect()


def execute_command(command: [], show_error=True) -> str:
    return subprocess.check_output(command, stderr=subprocess.DEVNULL)


def read_file_lines(filename: str) -> list:
    with open(filename) as f:
        return [line for line in f]


def get_default_configuration_for(config_name: str) -> str:
    logging.info(f'... get default configuration for [{config_name}]')
    config = '[]'
    for line in read_file_lines('./snap/hooks/install'):
        if config_name in line:
            config = line[str(line).index('=') + 2:-2]
    return config


def get_configuration(config_name: str) -> {}:
    value = None
    try:
        value = execute_command(["snapctl", "get", "-d", config_name]).strip()
        if len(value) < 3:
            value = execute_command(["snap", "get", "-d", "cubiemedia-mqtt-client", config_name]).strip()
    except:
        try:
            value = execute_command(["snap", "get", "-d", "cubiemedia-mqtt-client", config_name]).strip()
        except:
            logging.warning(
                f"seems to be a non snap environment, could not load config [{config_name}]\n"
                f"{COLOR_YELLOW}Try to install Snap locally to create config or login to Ubuntu with [snap login]{COLOR_DEFAULT}")
    if not value or len(value) < 3:
        value = get_default_configuration_for(config_name)
    json_object = json.loads(value)
    if config_name in json_object:
        return json_object[config_name]
    return json_object


def set_configuration(config_name: str, config: []):
    try:
        execute_command(["snapctl", "set", f"{config_name}={json.dumps(config)}"])
    except:
        try:
            execute_command(["snap", "set", "cubiemedia-mqtt-client", f"{config_name}={json.dumps(config)}"])
        except:
            logging.warning(
                f"seems to be a non snap environment, could not save config [{config_name}]\n"
                f"{COLOR_YELLOW}Try to install Snap locally to create config or login to Ubuntu with [snap login]{COLOR_DEFAULT}")
    return None


def install_package(package):
    subprocess.check_call(["python3", "-m", "pip", "install", package])
