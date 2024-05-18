import json
import logging
import subprocess
from functools import lru_cache
from json import JSONDecodeError
from os.path import exists

import common
from common import CUBIE_MQTT

USER_MESSAGE_SHOULD_BE_SHOWN = True

CONFIG_DICT = {
    common.CUBIE_MQTT: common.DEFAULT_CONFIGURATION_FILE_MQTT,
    common.CUBIE_SERIAL: common.DEFAULT_CONFIGURATION_FILE_SERIAL,
    common.CUBIE_GPIO: common.DEFAULT_CONFIGURATION_FILE_GPIO,
    common.CUBIE_SONAR: common.DEFAULT_CONFIGURATION_FILE_SONAR,
    common.CUBIE_RELAY: common.DEFAULT_CONFIGURATION_FILE_RELAY,
    common.CUBIE_VICTRON: common.DEFAULT_CONFIGURATION_FILE_VICTRON,
    common.CUBIE_ENOCEAN: common.DEFAULT_CONFIGURATION_FILE_ENOCEAN,
    common.CUBIE_MIFLORA: common.DEFAULT_CONFIGURATION_FILE_MIFLORA
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


def get_mqtt_configuration() -> {}:
    config = get_configuration(CUBIE_MQTT)
    if 'mqtt' not in config:
        raise RuntimeError("could not load mqtt config")
    return config['mqtt']


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


def system_reboot():
    execute_command("sleep 3")
