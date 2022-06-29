#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
import logging
import subprocess
import os

from common import CONFIG_FILE_NAME_RELAY, CUBIE_RELAY, CUBIE_GPIO, CUBIE_ENOCEAN, CONFIG_FILE_NAME_GPIO, \
    CONFIG_FILE_NAME_ENOCEAN


def get_config_file_name(execution_mode) -> str:
    snap_user_data = os.getenv('SNAP_USER_DATA')
    if execution_mode == CUBIE_RELAY:
        return f"{snap_user_data}/{CONFIG_FILE_NAME_RELAY}"
    elif execution_mode == CUBIE_GPIO:
        return f"{snap_user_data}/{CONFIG_FILE_NAME_GPIO}"
    elif execution_mode == CUBIE_ENOCEAN:
        return f"{snap_user_data}/{CONFIG_FILE_NAME_ENOCEAN}"

    raise RuntimeError(f"could not get config file name from execution mode[{execution_mode}]")


def exit_gracefully(system, *args):
    logging.info("... shutdown process")
    system.RUN = False

    system.shutdown()
    logging.info('... stopping MQTT Client...')
    system.mqtt_client.disconnect()


def install_package(package):
    subprocess.check_call(["python3", "-m", "pip", "install", package])
