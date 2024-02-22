#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import copy
import json
import logging
import subprocess
from os.path import exists

from common import COLOR_YELLOW, COLOR_DEFAULT, CUBIE_CORE, DEFAULT_CONFIGURATION_FILE_CORE, \
    DEFAULT_CONFIGURATION_FILE_SERIAL, DEFAULT_CONFIGURATION_FILE_SONAR, DEFAULT_CONFIGURATION_FILE_GPIO, \
    DEFAULT_CONFIGURATION_FILE_RELAY, DEFAULT_CONFIGURATION_FILE_VICTRON, DEFAULT_CONFIGURATION_FILE_ENOCEAN, \
    CUBIE_SERIAL, CUBIE_GPIO, CUBIE_SONAR, CUBIE_RELAY, CUBIE_VICTRON, CUBIE_ENOCEAN

USER_MESSAGE_SHOULD_BE_SHOWN = True

CONFIG_DICT = {
    CUBIE_CORE: DEFAULT_CONFIGURATION_FILE_CORE,
    CUBIE_SERIAL: DEFAULT_CONFIGURATION_FILE_SERIAL,
    CUBIE_GPIO: DEFAULT_CONFIGURATION_FILE_GPIO,
    CUBIE_SONAR: DEFAULT_CONFIGURATION_FILE_SONAR,
    CUBIE_RELAY: DEFAULT_CONFIGURATION_FILE_RELAY,
    CUBIE_VICTRON: DEFAULT_CONFIGURATION_FILE_VICTRON,
    CUBIE_ENOCEAN: DEFAULT_CONFIGURATION_FILE_ENOCEAN
}


def exit_gracefully(system, *args):
    logging.info("... shutdown process")
    system.RUN = False

    system.shutdown()
    if system.mqtt_client:
        logging.info('... stopping MQTT Client...')
        system.mqtt_client.disconnect()


def execute_command(command: []) -> str:
    return subprocess.check_output(command, stderr=subprocess.DEVNULL)


def get_variable_type_from_string(value: str):
    if value:
        if value.lower() == 'true' or value.lower() == 'false':
            return value.lower() == 'true'
        else:
            try:
                value = int(value)
            except:
                pass
    return value


def get_config_file_for(config_name: str) -> str:
    return CONFIG_DICT.get(config_name, f"Missing Config File for [{config_name}]")


def get_default_configuration_for(config_name: str) -> str:
    logging.debug(f'... get default configuration from config file for [{config_name}]')
    config_file = get_config_file_for(config_name)

    if not exists(config_file):
        config_file = "../" + config_file
        if not exists(config_file):
            config_file = "../" + config_file
            if not exists(config_file):
                raise FileNotFoundError(f"could not find config file [{config_file}]")
    with open(config_file) as file:
        config = json.load(file)
    return config


def set_default_configuration(config_name: str, config: []):
    logging.debug(f'... set default configuration to config file for [{config_name}]')
    config_file = get_config_file_for(config_name)

    if not exists(config_file):
        config_file = "../" + config_file
        if not exists(config_file):
            config_file = "../" + config_file
            if not exists(config_file):
                raise FileNotFoundError(f"could not find config file [{config_file}]")
    with open(config_file, 'w') as file:
        json.dump(config, file, indent=4, sort_keys=True)


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

    if value and len(value) > 3:
        return json.loads(value)
    else:
        return get_default_configuration_for(config_name)


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
