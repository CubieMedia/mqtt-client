import logging
import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock

from common import CUBIE_CORE
from common.network import get_ip_address
from common.python import get_configuration, get_default_configuration_for, set_default_configuration
from system.core_system import CoreSystem

ADDITIONAL_CORE_CONFIG = {
    "host": "testing",
    "id": "192.168.77.23",
    "learn_mode": True,
    "password": "something",
    "type": "core",
    "username": "admin"
}
DIFFERENT_CORE_CONFIG = {
    "host": "homeassistant",
    "id": get_ip_address(),
    "learn_mode": False,
    "password": "something",
    "type": "core",
    "username": "admin"
}


class TestCoreSystem(TestCase):
    mqtt_server_process = subprocess.Popen
    system = None
    config_backup = None

    def test_announce(self):
        self.system.mqtt_client.publish = MagicMock()
        self.system.set_availability = MagicMock()
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.publish.assert_called_once()
        self.system.set_availability.assert_called_once()

    def test_save_delete(self):
        self.system.init()
        time.sleep(1)

        assert len(self.system.config) == 1
        self.system.save(ADDITIONAL_CORE_CONFIG)
        assert len(self.system.config) == 2
        self.system.save(DIFFERENT_CORE_CONFIG)
        assert len(self.system.config) == 2
        assert self.system.config == [DIFFERENT_CORE_CONFIG, ADDITIONAL_CORE_CONFIG]
        self.system.delete(ADDITIONAL_CORE_CONFIG)
        assert len(self.system.config) == 1

    def setUp(self):
        self.system = CoreSystem()
        self.system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        cls.config_backup = get_default_configuration_for(CUBIE_CORE)
        # DODO check mosquitto already running
        try:
            cls.mqtt_server_process = subprocess.Popen("mosquitto")
            time.sleep(1)
        except FileNotFoundError:
            logging.error("could not start mosquitto [sudo apt install mosquitto]")

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_CORE, cls.config_backup)
        cls.mqtt_server_process.terminate()
        cls.mqtt_server_process.communicate()
