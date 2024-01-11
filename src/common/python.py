#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import copy
import json
import logging
import subprocess

from common import COLOR_YELLOW, COLOR_DEFAULT, DEFAULT_CONFIGURATION_FILE, CUBIE_CORE

USER_MESSAGE_SHOULD_BE_SHOWN = True


def exit_gracefully(system, *args):
    logging.info("... shutdown process")
    system.RUN = False

    system.shutdown()
    if system.mqtt_client:
        logging.info('... stopping MQTT Client...')
        system.mqtt_client.disconnect()


def execute_command(command: []) -> str:
    return subprocess.check_output(command, stderr=subprocess.DEVNULL)


def read_lines_from_file(filename: str) -> list:
    with open(filename) as f:
        return [line for line in f]


def save_lines_to_file(filename: str, config: list):
    with open(filename, 'w') as f:
        f.writelines(config)


def get_default_configuration_for(config_name: str) -> str:
    logging.info(f'... get default configuration from "snap/hooks/install" for [{config_name}]')
    config = '[]'
    for line in read_lines_from_file(DEFAULT_CONFIGURATION_FILE):
        if config_name in line:
            config = line[str(line).index('=') + 2:-2]
    return config


def set_default_configuration(config_name: str, config: []):
    config_read = read_lines_from_file(DEFAULT_CONFIGURATION_FILE)
    config_write = []
    for line in config_read:
        if config_name in line:
            line = line[0:str(line).index('=') + 2] + json.dumps(config) + "'\n"
        config_write.append(line)
    save_lines_to_file(DEFAULT_CONFIGURATION_FILE, config_write)


def get_configuration(config_name: str) -> []:
    global USER_MESSAGE_SHOULD_BE_SHOWN
    value = None
    try:
        value = execute_command(["snapctl", "get", "-d", config_name]).strip()
        if len(value) < 3:
            value = execute_command(["snap", "get", "-d", "cubiemedia-mqtt-client", config_name]).strip()
    except:
        try:
            value = execute_command(["snap", "get", "-d", "cubiemedia-mqtt-client", config_name]).strip()
        except:
            if USER_MESSAGE_SHOULD_BE_SHOWN:
                logging.warning(
                    f"seems to be a non snap environment, could not load config [{config_name}]\n"
                    f"{COLOR_YELLOW}Try to install Snap locally to create config or login to Ubuntu with [snap login]{COLOR_DEFAULT}")
                USER_MESSAGE_SHOULD_BE_SHOWN = False
    if not value or len(value) < 3:
        value = get_default_configuration_for(config_name)
    json_object = json.loads(value)
    if config_name in json_object:
        return json_object[config_name]
    return json_object


def get_core_configuration(ip: str) -> {}:
    core_configuration_list = get_configuration(CUBIE_CORE)
    for core_config in core_configuration_list:
        if 'id' in core_config:
            if core_config['id'] == ip:
                return core_config
        else:
            core_config['id'] = ip
            set_configuration(CUBIE_CORE, core_configuration_list)
            return core_config

    # no configuration found
    core_config = copy.copy(core_configuration_list[0]) if len(core_configuration_list) > 0 else {}
    core_config['id'] = ip
    core_configuration_list.append(core_config)
    set_configuration(CUBIE_CORE, core_configuration_list)
    return core_config


def set_configuration(config_name: str, config: []):
    global USER_MESSAGE_SHOULD_BE_SHOWN
    try:
        execute_command(["snapctl", "set", f"{config_name}={json.dumps(config)}"])
    except:
        try:
            execute_command(["snap", "set", "cubiemedia-mqtt-client", f"{config_name}={json.dumps(config)}"])
        except:
            if USER_MESSAGE_SHOULD_BE_SHOWN:
                logging.warning(
                    f"seems to be a non snap environment, could not save config [{config_name}]\n"
                    f"{COLOR_YELLOW}Try to install Snap locally to create config or login to Ubuntu with [snap login]{COLOR_DEFAULT}")
                USER_MESSAGE_SHOULD_BE_SHOWN = False
            set_default_configuration(config_name, config)
    return None


def install_package(package):
    subprocess.check_call(["python3", "-m", "pip", "install", package])
