import copy
import json
import logging
import subprocess
from functools import lru_cache
from json import JSONDecodeError
from os.path import exists

import common

USER_MESSAGE_SHOULD_BE_SHOWN = True

CONFIG_DICT = {
    common.CUBIE_CORE: common.DEFAULT_CONFIGURATION_FILE_CORE,
    common.CUBIE_SERIAL: common.DEFAULT_CONFIGURATION_FILE_SERIAL,
    common.CUBIE_GPIO: common.DEFAULT_CONFIGURATION_FILE_GPIO,
    common.CUBIE_SONAR: common.DEFAULT_CONFIGURATION_FILE_SONAR,
    common.CUBIE_RELAY: common.DEFAULT_CONFIGURATION_FILE_RELAY,
    common.CUBIE_VICTRON: common.DEFAULT_CONFIGURATION_FILE_VICTRON,
    common.CUBIE_ENOCEAN: common.DEFAULT_CONFIGURATION_FILE_ENOCEAN
}


def exit_gracefully(system, *args):
    logging.info("... shutdown mqtt client [" + str(args) + "]")
    system.RUN = False

    system.shutdown()
    if system.mqtt_client:
        logging.info('... stopping MQTT Client...')
        system.mqtt_client.disconnect()


def execute_command(command: []) -> str:
    try:
        result = subprocess.check_output(command, stderr=subprocess.STDOUT).decode()

        try:
            result_json = json.loads(result)
            if len(result_json) == 0:
                return "error: empty dict"
        except JSONDecodeError:
            pass
        return result
    except subprocess.CalledProcessError as e:
        return "error: " + str(e.output)
    except FileNotFoundError as e:
        return "error: " + str(e)


def get_variable_type_from_string(value: str):
    if value:
        if value.lower() == 'true' or value.lower() == 'false':
            return value.lower() == 'true'
        else:
            try:
                value = int(value)
            except ValueError:
                pass
    return value


def get_config_file_for(config_name: str) -> str:
    return CONFIG_DICT.get(config_name, f"Missing Config File for [{config_name}]")


def get_default_configuration_for(config_name: str) -> str:
    logging.debug('... get default configuration from config file for [%s]', config_name)
    config_file = get_config_file_for(config_name)

    if not exists(config_file):
        config_file = "../" + config_file
        if not exists(config_file):
            config_file = "../" + config_file
            if not exists(config_file):
                raise FileNotFoundError(f"could not find config file [{config_file}]")
    with open(config_file, encoding='utf-8') as file:
        config = json.load(file)
    return config


def set_default_configuration(config_name: str, config: []):
    logging.debug('... set default configuration to config file for [%s]', config_name)
    config_file = get_config_file_for(config_name)

    if not exists(config_file):
        config_file = "../" + config_file
        if not exists(config_file):
            config_file = "../" + config_file
            if not exists(config_file):
                raise FileNotFoundError(("could not find config file [%s]", config_file))
    with open(config_file, 'w', encoding='utf-8') as file:
        json.dump(config, file, indent=2, sort_keys=True)


def get_configuration(config_name: str) -> []:
    value = execute_command(["snapctl", "get", "-d", config_name]).strip()
    if 'error' in value:
        value = execute_command(["snap", "get", "-d", "cubiemedia-mqtt-client", config_name])

    if 'error' in value:
        warn_once(
            "%sseems to be a non snap environment, could not load config [%s]\n"
            "Try to install Snap locally to create config or login to Ubuntu with [snap login]%s",
            common.COLOR_YELLOW, config_name, common.COLOR_DEFAULT)
        return get_default_configuration_for(config_name)
    else:
        return json.loads(value)


def get_core_configuration(ip: str) -> {}:
    core_configuration_list = get_configuration(common.CUBIE_CORE)
    for core_config in core_configuration_list:
        if 'id' in core_config:
            if core_config['id'] == ip:
                return core_config
        else:
            core_config['id'] = ip
            set_configuration(common.CUBIE_CORE, core_configuration_list)
            return core_config

    # no configuration found
    core_config = copy.copy(core_configuration_list[0]) if len(core_configuration_list) > 0 else {}
    core_config['id'] = ip
    core_configuration_list.append(core_config)
    set_configuration(common.CUBIE_CORE, core_configuration_list)
    return core_config


def set_configuration(config_name: str, config: []):
    result = execute_command(["snapctl", "set", f"{config_name}={json.dumps(config)}"])
    if 'error' in result:
        result = execute_command(
            ["snap", "set", "cubiemedia-mqtt-client", f"{config_name}={json.dumps(config)}"])
    if 'error' in result:
        set_default_configuration(config_name, config)


@lru_cache(10)
def warn_once(msg: str, *args):
    logging.warning(msg, *args)


def install_package(package):
    subprocess.check_call(["python3", "-m", "pip", "install", package])
