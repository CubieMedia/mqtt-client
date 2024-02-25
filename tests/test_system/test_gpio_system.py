import logging
import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock

from common import CUBIE_CORE, CUBIE_GPIO
from common.python import set_default_configuration, get_default_configuration_for
from system.gpio_system import GPIOSystem
from test_common import check_mqtt_server, AUTHENTICATION_MOCK

DEVICE_TEST = {"id": "Test", "type": "relay", "value": 0}
DATA_TEST = {"ip": "Test", "type": "relay", "id": 3, "state": b"0"}


class TestGPIOSystem(TestCase):
    config_backup = None
    gpio_backup = None
    mqtt_server_process = subprocess.Popen
    system = None

    def test_action(self):
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.publish = MagicMock()
        response = self.system.action(None)
        time.sleep(1)

        assert not response
        self.system.mqtt_client.publish.assert_not_called()

        self.system.mqtt_client.publish = MagicMock()
        response = self.system.action({})
        time.sleep(1)

        assert not response
        self.system.mqtt_client.publish.assert_not_called()

        self.system.mqtt_client.publish = MagicMock()
        response = self.system.action(DEVICE_TEST)
        time.sleep(1)

        assert response
        self.system.mqtt_client.publish.assert_called_once()

    def test_send(self):
        self.system.init()
        time.sleep(1)

        self.system.gpio_control = MagicMock()
        self.system.send(DATA_TEST)

        self.system.gpio_control.output.assert_called_with(int(DATA_TEST['id']),
                                                           0 if int(DATA_TEST['state'].decode()) == 1 else 1)

    def test_update(self):
        self.system.init()
        time.sleep(1)

        data = self.system.update()
        assert len(data['devices']) > 0

    def test_set_availability(self):
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client = MagicMock()
        self.system.set_availability(False)

        self.system.mqtt_client.publish.assert_called_once()
        self.system.mqtt_client.reset_mock()
        self.system.set_availability(True)

        assert len(self.system.mqtt_client.publish.mock_calls) == 9

    def test_init(self):
        self.system.gpio_control = MagicMock()
        self.system.init()
        time.sleep(1)

        assert self.system.mqtt_client.mqtt_client.is_connected()
        assert len(self.system.gpio_control.setup.mock_calls) == 8
        assert len(self.system.gpio_control.output.mock_calls) == 4

    def test_shutdown(self):
        self.test_init()

        self.system.gpio_control = MagicMock()
        self.system.shutdown()
        time.sleep(1)

        assert not self.system.mqtt_client.mqtt_client.is_connected()
        self.system.gpio_control.cleanup.assert_called_once()

    def test_announce(self):
        self.system.set_availability = MagicMock()
        self.system.mqtt_client.mqtt_client.subscribe = MagicMock()
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.mqtt_client.subscribe.assert_called()
        self.system.set_availability.assert_called()

    def setUp(self):
        self.system = GPIOSystem()
        self.system.get_mqtt_data = AUTHENTICATION_MOCK

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        cls.config_backup = get_default_configuration_for(CUBIE_CORE)
        cls.gpio_backup = get_default_configuration_for(CUBIE_GPIO)
        cls.mqtt_server_process = check_mqtt_server()

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_CORE, cls.config_backup)
        set_default_configuration(CUBIE_GPIO, cls.gpio_backup)
        if cls.mqtt_server_process:
            cls.mqtt_server_process.terminate()
            cls.mqtt_server_process.communicate()
