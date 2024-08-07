import logging
import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock

from common import CUBIE_SYSTEM, CUBIE_RELAY
from common.python import set_default_configuration, get_default_configuration_for
from system.relay_system import RelaySystem
from test_common import check_mqtt_server, MQTT_HOST_MOCK, MQTT_LOGIN_MOCK

DEVICE_TEST = {"id": "Test", "type": "relay", "state": {1: 0, 2: 0, 3: 0}}
DATA_TEST = {"ip": "Test", "type": "relay", "id": 3, "state": "1"}


class TestRelaySystem(TestCase):
    config_backup = None
    relay_backup = None
    mqtt_server_process = subprocess.Popen
    system = None

    def test_action(self):
        self.system.mqtt_client.subscribe = MagicMock()
        self.system.mqtt_client.publish = MagicMock()
        assert not self.system.action(DEVICE_TEST)
        self.system.mqtt_client.subscribe.assert_not_called()
        self.system.mqtt_client.publish.assert_not_called()

        self.system.config.append(DEVICE_TEST)

        assert self.system.action(DEVICE_TEST)

        self.system.mqtt_client.subscribe.assert_not_called()
        assert len(self.system.mqtt_client.publish.mock_calls) == len(DEVICE_TEST['state'].keys())
        self.system.config.clear()

    def test_send(self):
        self.system.init()
        time.sleep(1)

        self.system.config.append(DEVICE_TEST)
        self.system._set_status = MagicMock()
        self.system.send(DATA_TEST)

        self.system._set_status.assert_called_with("Test", 3, "1", False)
        self.system.config.clear()

    def test_update(self):
        data = self.system.update()
        assert data == {}, "Fast Check failed, did i really find Relay Boards?"
        time.sleep(1)

        self.system.last_update = -1
        data = self.system.update()
        if 'devices' in data:
            assert len(data['devices']) == len(self.system.relay_board_list)
        else:
            assert len(
                self.system.relay_board_list) == 0, f"module list [{self.system.relay_board_list}] is not empty!"

    def test_set_availability(self):
        self.system.mqtt_client.publish = MagicMock()

        self.system.mqtt_client.publish.assert_not_called()
        self.system.init()
        self.system.save(DEVICE_TEST)
        self.system.mqtt_client = MagicMock()
        self.system.set_availability(False)

        assert len(self.system.mqtt_client.publish.mock_calls) == 2
        self.system.delete(DEVICE_TEST)

    def test_init(self):
        self.system.init()
        time.sleep(1)

        assert self.system.mqtt_client.mqtt_client.is_connected()
        assert not self.system.scan_thread_event.is_set()
        assert self.system.scan_thread.is_alive()

    def test_shutdown(self):
        self.test_init()

        self.system.shutdown()
        time.sleep(1)

        assert not self.system.mqtt_client.mqtt_client.is_connected()
        assert self.system.scan_thread_event.is_set()
        assert not self.system.scan_thread.is_alive()

    def test_announce(self):
        self.system.set_availability = MagicMock()
        self.system.mqtt_client.mqtt_client.subscribe = MagicMock()
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.mqtt_client.subscribe.assert_called()
        self.system.set_availability.assert_called()

    def setUp(self):
        self.system = RelaySystem()
        self.system.get_mqtt_server = MQTT_HOST_MOCK
        self.system.get_mqtt_login = MQTT_LOGIN_MOCK

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        cls.config_backup = get_default_configuration_for(CUBIE_SYSTEM)
        cls.relay_backup = get_default_configuration_for(CUBIE_RELAY)
        cls.mqtt_server_process = check_mqtt_server()

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_SYSTEM, cls.config_backup)
        set_default_configuration(CUBIE_RELAY, cls.relay_backup)
        if cls.mqtt_server_process:
            cls.mqtt_server_process.terminate()
            cls.mqtt_server_process.communicate()
