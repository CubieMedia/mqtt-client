#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import logging
import subprocess


def exit_gracefully(system, *args):
    logging.info("... shutdown process")
    system.RUN = False

    system.shutdown()
    logging.info('... stopping MQTT Client...')
    system.mqtt_client.disconnect()


def execute_command(command: []):
    subprocess.check_output(command)


def get_configuration(config_name: str) -> {}:
    return execute_command(["snapctl", "get", "-d", config_name])


def set_configuration(config_name: str, config: {}):
    execute_command(["snapctl", "set", f"{config_name}={config}"])


def install_package(package):
    subprocess.check_call(["python3", "-m", "pip", "install", package])
