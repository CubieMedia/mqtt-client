import logging
import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock

from common import CUBIE_CORE, CUBIE_RELAY
from common.python import set_default_configuration, get_default_configuration_for
from system.relay_system import RelaySystem
from test_common import check_mqtt_server, AUTHENTICATION_MOCK

DEVICE_TEST = {"id": "Test", "type": "relay"}
DATA_TEST = {"ip": "Test", "type": "relay", "id": 3, "state": "1"}


class TestRelaySystem(TestCase):
    config_backup = None
    relay_backup = None
    mqtt_server_process = subprocess.Popen
    system = None

    def test_action(self):
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.subscribe = MagicMock()
        self.system.mqtt_client.publish = MagicMock()
        self.system.action(DEVICE_TEST)
        time.sleep(1)

        self.system.mqtt_client.subscribe.assert_called_once()
        self.system.mqtt_client.publish.assert_called_once()
        assert DEVICE_TEST['id'] in self.system.subscription_list
        assert len(self.system.subscription_list) == 1

        self.system.mqtt_client.publish.reset_mock()
        self.system.action(DEVICE_TEST)
        time.sleep(1)

        self.system.mqtt_client.subscribe.assert_called_once()
        self.system.mqtt_client.publish.assert_called_once()
        assert DEVICE_TEST['id'] in self.system.subscription_list
        assert len(self.system.subscription_list) == 1

    def test_send(self):
        self.system.init()
        time.sleep(1)

        self.system._set_status = MagicMock()
        self.system.send(DATA_TEST)

        self.system._set_status.assert_called_with("Test", 3, "1", False)

    def test_update(self):
        self.system.init()
        data = self.system.update()
        assert data == {}, "Fast Check failed, did i really find Relay Boards?"
        time.sleep(1)

        data = self.system.update()
        if len(self.system.module_list) > 0:
            assert len(data) > 0
        else:
            assert data == {}

    def test_set_availability(self):
        self.system.mqtt_client = MagicMock()
        self.system.set_availability(False)

        self.system.mqtt_client.publish.assert_not_called()
        self.system.init()
        self.system.save(DEVICE_TEST)
        self.system.mqtt_client = MagicMock()
        self.system.set_availability(False)

        self.system.mqtt_client.publish.assert_called_once()

    def test_init(self):
        self.system.init()
        time.sleep(1)

        assert self.system.mqtt_client.mqtt_client.is_connected()
        assert not self.system.scan_thread_event.is_set()
        assert self.system.scan_thread.is_alive()

    def test_shutdown(self):
        self.system.init()
        time.sleep(1)

        assert self.system.mqtt_client.mqtt_client.is_connected()
        assert not self.system.scan_thread_event.is_set()
        assert self.system.scan_thread.is_alive()

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
        self.system.get_mqtt_data = AUTHENTICATION_MOCK

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)
        cls.config_backup = get_default_configuration_for(CUBIE_CORE)
        cls.relay_backup = get_default_configuration_for(CUBIE_RELAY)
        cls.mqtt_server_process = check_mqtt_server()

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_CORE, cls.config_backup)
        set_default_configuration(CUBIE_RELAY, cls.relay_backup)
        if cls.mqtt_server_process:
            cls.mqtt_server_process.terminate()
            cls.mqtt_server_process.communicate()
