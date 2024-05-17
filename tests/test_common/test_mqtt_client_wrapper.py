import logging
import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock, create_autospec

import pytest

from common import CUBIE_ANNOUNCE, CUBIE_RESET, CUBIE_RELOAD, CUBIE_MQTT
from common.python import get_default_configuration_for, set_default_configuration
from system.base_system import BaseSystem
from test_common import check_mqtt_server, MQTT_HOST_MOCK


class TestCubieMediaMQTTClient(TestCase):
    backup_config = None
    mqtt_server_process = subprocess.Popen
    system = None

    def test_connect_disconnect(self):
        self.system.get_mqtt_server = MagicMock(return_value="192.168.11.7")
        with pytest.raises((TimeoutError, ConnectionRefusedError, OSError)):  # noqa
            self.system.init()
        self.system.get_mqtt_server.assert_called_once()
        assert not self.system.mqtt_client.mqtt_client.is_connected()

        self.system = BaseSystem()
        self.system.get_mqtt_server = MQTT_HOST_MOCK
        self.system.init()

        self.system.get_mqtt_server.assert_called_once()
        self.system.get_mqtt_server.reset_mock()
        time.sleep(1)
        assert self.system.mqtt_client.mqtt_client.is_connected()
        self.system.get_mqtt_server.assert_called_once()

        self.system.mqtt_client.disconnect()
        time.sleep(1)
        self.system.get_mqtt_server.assert_called_once()
        assert not self.system.mqtt_client.mqtt_client.is_connected()

        self.system.mqtt_client.connect(self.system)
        time.sleep(1)
        self.system.get_mqtt_server.assert_called()
        assert self.system.mqtt_client.mqtt_client.is_connected()

    def test_publish(self):
        self.system.init()
        time.sleep(1)

        autospec_publish = create_autospec(self.system.mqtt_client.publish)
        with pytest.raises(TypeError):
            autospec_publish()
            autospec_publish("Topic")
        autospec_publish("Topic", "Howdy ho!")
        autospec_publish("Topic", "Howdy ho!", True)
        autospec_publish("Topic", "Howdy ho!", False)

        autospec_publish.assert_called()

    def test_subscribe(self):
        self.system.init()
        time.sleep(1)

        autospec_publish = create_autospec(self.system.mqtt_client.subscribe)
        with pytest.raises(TypeError):
            autospec_publish()
            autospec_publish("Topic")
        autospec_publish("Topic", 0)
        autospec_publish("Topic", 1)
        autospec_publish("Topic", 2)

        autospec_publish.assert_called()

    def test_on_message(self):
        self.system.announce = MagicMock()
        self.system.init()
        time.sleep(1)

        self.system.announce = MagicMock()
        self.system.reset = MagicMock()
        self.system.load = MagicMock()
        msg = MagicMock()
        msg.payload = CUBIE_ANNOUNCE.encode('UTF-8')
        self.system.mqtt_client.on_message(None, None, msg)

        msg.payload = CUBIE_RESET.encode('UTF-8')
        self.system.mqtt_client.on_message(None, None, msg)

        msg.payload = CUBIE_RELOAD.encode('UTF-8')
        self.system.mqtt_client.on_message(None, None, msg)

        self.system.announce.assert_called_once()
        self.system.reset.assert_called_once()
        self.system.load.assert_called_once()

    def test_on_connect(self):
        self.system.announce = MagicMock()
        self.system.mqtt_client.mqtt_client.subscribe = MagicMock()
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.mqtt_client.is_connected()
        self.system.announce.assert_called_once()
        self.system.mqtt_client.mqtt_client.subscribe.assert_called()

    def test_on_disconnect(self):
        self.system.announce = MagicMock()
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.on_disconnect = MagicMock()
        self.system.mqtt_client.mqtt_client.on_disconnect = self.system.mqtt_client.on_disconnect
        self.system.announce.assert_called_once()
        self.system.mqtt_client.on_disconnect.assert_not_called()

        self.system.shutdown()
        time.sleep(1)
        self.system.mqtt_client.on_disconnect.assert_called_once()

    def setUp(self):
        self.system = BaseSystem()
        self.system.get_mqtt_server = MQTT_HOST_MOCK

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)
        cls.backup_config = get_default_configuration_for(CUBIE_MQTT)
        cls.mqtt_server_process = check_mqtt_server()

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_MQTT, cls.backup_config)
        if cls.mqtt_server_process:
            cls.mqtt_server_process.terminate()
            cls.mqtt_server_process.communicate()
