#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import logging
import signal
import sys
import time
import warnings
from functools import partial

from common import CUBIE_IO, CUBIE_ENOCEAN, CUBIE_RELAY, COLOR_DEFAULT, COLOR_RED  # noqa
from common.network import get_ip_address  # noqa
from common.python import exit_gracefully


def get_execution_mode(argv: []) -> str:
    if len(argv) < 2 or (argv[1] != CUBIE_IO and argv[1] != CUBIE_ENOCEAN and argv[1] != CUBIE_RELAY):
        raise RuntimeError(f"Please give Mode [%s,%s,%s] for script" % (CUBIE_IO, CUBIE_ENOCEAN, CUBIE_RELAY))

    return argv[1]


def is_verbose(argv: []) -> bool:
    for arg in argv:
        if 'verbose' in arg:
            return True

    return False


def configure_logger():
    logging.basicConfig(level=logging.DEBUG if is_verbose(sys.argv) else logging.INFO,
                        format='%(asctime)s - %(levelname)-8s - %(message)s')

    # added for enocean module bug with wrong parser configuration
    warnings.simplefilter("ignore")

#    logging.getLogger().addHandler(StreamHandler(sys.stdout))
#    logging.getLogger().addHandler(SysLogHandler(address='/dev/log'))


def get_system(execution_mode: str):
    if execution_mode == CUBIE_IO:
        from system.gpio_system import GPIOSystem
        return GPIOSystem()
    elif execution_mode == CUBIE_ENOCEAN:
        from system.enocean_system import EnoceanSystem
        return EnoceanSystem()
    elif execution_mode == CUBIE_RELAY:
        from system.relay_system import RelaySystem
        return RelaySystem()
    else:
        raise RuntimeError(f"could not find system for mode[{execution_mode}]")


def main():
    configure_logger()
    mode = get_execution_mode(sys.argv)

    logging.info("Starting Cubie MQTT Client with mode [%s]" % mode)

    ip_address = get_ip_address()
    system = get_system(mode)
    client_id = ip_address + "-" + mode + "-client"
    system.init(client_id)
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


if __name__ == '__main__':
    try:
        sys.exit(main())
    except RuntimeError as e:
        if is_verbose(sys.argv):
            raise e
        else:
            logging.error(e)

    sys.exit(1)
