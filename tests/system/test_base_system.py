import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock

from common import DEFAULT_MQTT_SERVER, DEFAULT_LEARN_MODE, DEFAULT_MQTT_PASSWORD, DEFAULT_MQTT_USERNAME, CUBIEMEDIA
from system.base_system import BaseSystem

DEVICE_TEST = {"id": "Test"}
DEVICE_TEST2 = {"id": "Test2"}


class TestBaseSystem(TestCase):
    mqtt_server_process = None

    def test_set_availability(self):
        mqtt_server_process = subprocess.Popen("mosquitto")
        time.sleep(1)

        system = BaseSystem()
        system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))
        system.init()
        time.sleep(1)

        system.mqtt_client.publish = MagicMock()
        system.set_availability(True)
        system.mqtt_client.publish.assert_called_with(
            f"{CUBIEMEDIA}/{system.execution_mode}/{system.ip_address.replace('.', '_')}/online", "true")

        system.set_availability(False)
        system.mqtt_client.publish.assert_called_with(
            f"{CUBIEMEDIA}/{system.execution_mode}/{system.ip_address.replace('.', '_')}/online", "false")

        mqtt_server_process.terminate()
        mqtt_server_process.communicate()

    def test_load(self):
        system = BaseSystem()
        system.load()

        assert system.mqtt_server == DEFAULT_MQTT_SERVER
        assert system.mqtt_user == DEFAULT_MQTT_USERNAME
        assert system.mqtt_password == DEFAULT_MQTT_PASSWORD
        assert system.learn_mode == DEFAULT_LEARN_MODE
        assert system.known_device_list == []

    def test_save(self):
        system = BaseSystem()
        system.load()

        assert system.known_device_list == []

        system.save()
        assert system.known_device_list == []

        system.save(DEVICE_TEST)
        altered_device = DEVICE_TEST.copy()
        altered_device['something'] = "ihavebeenset"
        system.save(altered_device)
        assert system.known_device_list == [altered_device]

        system.save(DEVICE_TEST2)
        assert system.known_device_list == [altered_device, DEVICE_TEST2]

        system.save()
        assert system.known_device_list == [altered_device, DEVICE_TEST2]

    def test_delete(self):
        system = BaseSystem()
        system.load()

        system.save(DEVICE_TEST)
        system.save(DEVICE_TEST2)
        assert system.known_device_list == [DEVICE_TEST, DEVICE_TEST2]

        system.delete(DEVICE_TEST)
        assert system.known_device_list == [DEVICE_TEST2]

        system.delete(DEVICE_TEST2)
        assert system.known_device_list == []

    def test_reset(self):
        system = BaseSystem()
        system.load()

        assert system.known_device_list == []

        system.save(DEVICE_TEST)
        system.save(DEVICE_TEST2)
        assert system.known_device_list == [DEVICE_TEST, DEVICE_TEST2]

        system.reset()
        assert system.known_device_list == []
