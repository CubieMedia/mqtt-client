#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging
import signal
import sys
import time
import warnings
from functools import partial

import common
from common.python import exit_gracefully


def get_execution_mode() -> str:
    for arg in sys.argv:
        arg = arg.lower()
        if arg in common.CUBIE_MODE_LIST:
            return arg

    raise RuntimeError(f"Please give Mode [{common.CUBIE_MODE_LIST}] for script")


def is_verbose() -> bool:
    for arg in sys.argv:
        if 'verbose' in arg or 'debug' in arg:
            return True

    return False


def configure_logger():
    debug = is_verbose()
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO,
                        format='%(asctime)s - %(levelname)-8s - %(message)s')

    # added for enocean module bug with wrong parser configuration
    warnings.simplefilter("ignore")
    # added for flask
    if not debug:
        werkzeug = logging.getLogger('werkzeug')
        werkzeug.setLevel(logging.ERROR)


def get_system(execution_mode: str):

    if execution_mode == common.CUBIE_GPIO:
        from system.gpio_system import GPIOSystem
        return GPIOSystem()
    if execution_mode == common.CUBIE_ENOCEAN:
        from system.enocean_system import EnoceanSystem
        return EnoceanSystem()
    if execution_mode == common.CUBIE_RELAY:
        from system.relay_system import RelaySystem
        return RelaySystem()
    if execution_mode == common.CUBIE_SONAR:
        from system.sonar_system import SonarSystem
        return SonarSystem()
    if execution_mode == common.CUBIE_VICTRON:
        from system.victron_system import VictronSystem
        return VictronSystem()
    if execution_mode == common.CUBIE_MIFLORA:
        from system.miflora_system import MiFloraSystem
        return MiFloraSystem()
    if execution_mode == common.CUBIE_BALBOA:
        from system.balboa_system import BalboaSystem
        return BalboaSystem()

    raise RuntimeError(f"could not find system for mode[{execution_mode}]")


def main():
    try:
        configure_logger()
        mode = get_execution_mode()

        logging.info("Starting Cubie MQTT Client with mode [%s]", mode)

        system = get_system(mode)
        system.init()

        # noinspection PyTypeChecker
        signal.signal(signal.SIGINT, partial(exit_gracefully, system))
        # noinspection PyTypeChecker
        signal.signal(signal.SIGTERM, partial(exit_gracefully, system))

        system.RUN = True
        while system.RUN:
            data = system.update()

            if 'devices' in data and len(data['devices']) > 0:
                devices = data['devices']
                for device in devices:
                    system.action(device)

            time.sleep(.2)

        logging.info('all done, exit program')
    except RuntimeError as exception:
        logging.error(exception)
        if "Try running as root!" in str(exception):
            logging.error("%sPlease connect plugs [gpio-memory-control |"
                          " serial-port]%s", common.COLOR_RED, common.COLOR_DEFAULT)
        if is_verbose():
            raise exception


if __name__ == '__main__':
    try:
        sys.exit(main())
    except RuntimeError as e:
        logging.error(e)
        if is_verbose():
            raise e

    sys.exit(0)
