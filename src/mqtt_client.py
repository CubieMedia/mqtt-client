#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging
import signal
import sys
import time
import warnings
from functools import partial

from common import CUBIE_GPIO, CUBIE_ENOCEAN, CUBIE_RELAY, COLOR_DEFAULT, COLOR_RED, CUBIE_SONAR, CUBIE_VICTRON, \
    CUBIE_CORE  # noqa
from common.network import get_ip_address  # noqa
from common.python import exit_gracefully


def get_execution_mode() -> str:
    for arg in sys.argv:
        if arg == CUBIE_GPIO:
            return CUBIE_GPIO
        elif arg == CUBIE_ENOCEAN:
            return CUBIE_ENOCEAN
        elif arg == CUBIE_RELAY:
            return CUBIE_RELAY
        elif arg == CUBIE_VICTRON:
            return CUBIE_VICTRON
        elif arg == CUBIE_SONAR:
            return CUBIE_SONAR
        elif arg == CUBIE_CORE:
            return CUBIE_CORE

    raise RuntimeError(
        f"Please give Mode [%s,%s,%s,%s,%s,%s] for script" % (
            CUBIE_CORE, CUBIE_GPIO, CUBIE_ENOCEAN, CUBIE_RELAY, CUBIE_SONAR, CUBIE_VICTRON))


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
    if execution_mode == CUBIE_GPIO:
        from system.gpio_system import GPIOSystem
        return GPIOSystem()
    elif execution_mode == CUBIE_ENOCEAN:
        from system.enocean_system import EnoceanSystem
        return EnoceanSystem()
    elif execution_mode == CUBIE_RELAY:
        from system.relay_system import RelaySystem
        return RelaySystem()
    elif execution_mode == CUBIE_SONAR:
        from system.sonar_system import SonarSystem
        return SonarSystem()
    elif execution_mode == CUBIE_VICTRON:
        from system.victron_system import VictronSystem
        return VictronSystem()
    elif execution_mode == CUBIE_CORE:
        from system.core_system import CoreSystem
        return CoreSystem()
    else:
        raise RuntimeError(f"could not find system for mode[{execution_mode}]")


def main():
    try:
        configure_logger()
        mode = get_execution_mode()

        logging.info("Starting Cubie MQTT Client with mode [%s]" % mode)

        ip_address = get_ip_address()
        system = get_system(mode)
        system.init(ip_address)
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
        if is_verbose():
            raise exception
        else:
            logging.error(exception)
        if "Try running as root!" in exception.__str__():
            logging.error(
                f"{COLOR_RED}Also remember to connect plugs [gpio-memory-control | serial-port]{COLOR_DEFAULT}")


if __name__ == '__main__':
    try:
        sys.exit(main())
    except RuntimeError as e:
        if is_verbose():
            raise e
        else:
            logging.error(e)

    sys.exit(0)
