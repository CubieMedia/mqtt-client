import logging
import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock, create_autospec

import pytest

from common import CUBIE_ANNOUNCE, CUBIE_RESET, CUBIE_RELOAD
from system.base_system import BaseSystem


class TestCubieMediaMQTTClient(TestCase):
    mqtt_server_process = subprocess.Popen
    system = None

    def test_connect_disconnect(self):
        self.system.get_mqtt_data = MagicMock(return_value=("192.168.11.7", None, None))
        with pytest.raises(TimeoutError) or pytest.raises(ConnectionRefusedError):
            self.system.init()
        time.sleep(1)

        self.system.get_mqtt_data.assert_called_once()
        assert not self.system.mqtt_client.mqtt_client.is_connected()

        self.system = BaseSystem()
        self.system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
        self.system.init()
        time.sleep(1)

        self.system.get_mqtt_data.assert_called_once()
        assert self.system.mqtt_client.mqtt_client.is_connected()

        self.system.mqtt_client.disconnect()
        time.sleep(1)
        self.system.get_mqtt_data.assert_called_once()
        assert not self.system.mqtt_client.mqtt_client.is_connected()

        self.system.mqtt_client.connect(self.system)
        time.sleep(1)
        self.system.get_mqtt_data.assert_called()
        assert self.system.mqtt_client.mqtt_client.is_connected()

    def test_publish(self):
        self.system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
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
        self.system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
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
        self.system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
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
        self.system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
        self.system.announce = MagicMock()
        self.system.init()
        time.sleep(1)

        self.system.announce.assert_called_once()

    def test_on_disconnect(self):
        self.system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
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

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        try:
            cls.mqtt_server_process = subprocess.Popen("mosquitto")
            time.sleep(1)
        except FileNotFoundError:
            logging.error("could not start mosquitto [sudo apt install mosquitto]")

    @classmethod
    def tearDownClass(cls):
        cls.mqtt_server_process.terminate()
        cls.mqtt_server_process.communicate()
