import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock, create_autospec

import pytest

from common import CUBIE_ANNOUNCE, CUBIE_RESET, CUBIE_RELOAD
from system.base_system import BaseSystem


class TestCubieMediaMQTTClient(TestCase):
    mqtt_server_process = subprocess.Popen

    def test_connect_disconnect(self):
        system = BaseSystem()
        system.get_mqtt_data = MagicMock(return_value=("192.168.11.7", None, None))
        with pytest.raises(TimeoutError) or pytest.raises(ConnectionRefusedError):
            system.init()
        time.sleep(1)

        system.get_mqtt_data.assert_called_once()
        assert not system.mqtt_client.mqtt_client.is_connected()

        system = BaseSystem()
        system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
        system.init()
        time.sleep(1)

        system.get_mqtt_data.assert_called_once()
        assert system.mqtt_client.mqtt_client.is_connected()

        system.mqtt_client.disconnect()
        time.sleep(1)
        system.get_mqtt_data.assert_called_once()
        assert not system.mqtt_client.mqtt_client.is_connected()

        system.mqtt_client.connect(system)
        time.sleep(1)
        system.get_mqtt_data.assert_called()
        assert system.mqtt_client.mqtt_client.is_connected()

    def test_publish(self):
        system = BaseSystem()
        system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
        system.init()
        time.sleep(1)

        autospec_publish = create_autospec(system.mqtt_client.publish)
        with pytest.raises(TypeError):
            autospec_publish()
            autospec_publish("Topic")
        autospec_publish("Topic", "Howdy ho!")
        autospec_publish("Topic", "Howdy ho!", True)
        autospec_publish("Topic", "Howdy ho!", False)

        autospec_publish.assert_called()

    def test_subscribe(self):
        system = BaseSystem()
        system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
        system.init()
        time.sleep(1)

        autospec_publish = create_autospec(system.mqtt_client.subscribe)
        with pytest.raises(TypeError):
            autospec_publish()
            autospec_publish("Topic")
        autospec_publish("Topic", 0)
        autospec_publish("Topic", 1)
        autospec_publish("Topic", 2)

        autospec_publish.assert_called()

    def test_on_message(self):
        system = BaseSystem()
        system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
        system.announce = MagicMock()
        system.init()
        time.sleep(1)

        system.announce = MagicMock()
        system.reset = MagicMock()
        system.load = MagicMock()
        msg = MagicMock()
        msg.payload = CUBIE_ANNOUNCE.encode('UTF-8')
        system.mqtt_client.on_message(None, None, msg)

        msg.payload = CUBIE_RESET.encode('UTF-8')
        system.mqtt_client.on_message(None, None, msg)

        msg.payload = CUBIE_RELOAD.encode('UTF-8')
        system.mqtt_client.on_message(None, None, msg)

        system.announce.assert_called_once()
        system.reset.assert_called_once()
        system.load.assert_called_once()

    def test_on_connect(self):
        system = BaseSystem()
        system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
        system.announce = MagicMock()
        system.init()
        time.sleep(1)

        system.announce.assert_called_once()

    def test_on_disconnect(self):
        system = BaseSystem()
        system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
        system.announce = MagicMock()
        system.init()
        time.sleep(1)

        system.mqtt_client.on_disconnect = MagicMock()
        system.mqtt_client.mqtt_client.on_disconnect = system.mqtt_client.on_disconnect
        system.announce.assert_called_once()
        system.mqtt_client.on_disconnect.assert_not_called()

        system.shutdown()
        time.sleep(1)
        system.mqtt_client.on_disconnect.assert_called_once()

    @classmethod
    def setUpClass(cls):
        cls.mqtt_server_process = subprocess.Popen("mosquitto")
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.mqtt_server_process.terminate()
        cls.mqtt_server_process.communicate()
