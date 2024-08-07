import time
from unittest import TestCase
from unittest.mock import MagicMock

from common import MQTT_CUBIEMEDIA, DEFAULT_MQTT_SERVER, DEFAULT_MQTT_USERNAME, \
    DEFAULT_MQTT_PASSWORD, CUBIE_SYSTEM
from common.python import get_default_configuration_for, set_default_configuration
from system.base_system import BaseSystem
from test_common import MQTT_HOST_MOCK, check_mqtt_server, MQTT_LOGIN_MOCK

DEVICE_TEST = {"id": "Test"}
DEVICE_TEST2 = {"id": "Test2"}


class TestBaseSystem(TestCase):
    config_backup = None
    mqtt_server_process = None
    system = None

    def test_set_availability(self):
        self.mqtt_server_process = check_mqtt_server()

        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.publish = MagicMock()
        self.system.set_availability(True)
        self.system.mqtt_client.publish.assert_called_with(
            f"{MQTT_CUBIEMEDIA}/{self.system.execution_mode}/{self.system.ip_address.replace('.', '_')}/online",
            "true")

        self.system.set_availability(False)
        self.system.mqtt_client.publish.assert_called_with(
            f"{MQTT_CUBIEMEDIA}/{self.system.execution_mode}/{self.system.ip_address.replace('.', '_')}/online",
            "false")

    def test_load(self):
        self.system.load()

        assert self.system.get_mqtt_server() == DEFAULT_MQTT_SERVER
        assert self.system.get_mqtt_login()[0] == DEFAULT_MQTT_USERNAME
        assert self.system.get_mqtt_login()[1] == DEFAULT_MQTT_PASSWORD
        assert self.system.config == []

    def test_save(self):
        self.system.load()
        self.system.reset()

        assert self.system.config == []

        self.system.save()
        assert self.system.config == []

        altered_device = DEVICE_TEST.copy()
        altered_device['something'] = "ihavebeenset"
        self.system.save(altered_device)
        assert self.system.config == [altered_device]

        self.system.save(DEVICE_TEST2)
        assert self.system.config == [altered_device, DEVICE_TEST2]

        self.system.save()
        assert self.system.config == [altered_device, DEVICE_TEST2]

    def test_delete(self):
        self.system.load()

        self.system.save(DEVICE_TEST)
        self.system.save(DEVICE_TEST2)
        assert self.system.config == [DEVICE_TEST, DEVICE_TEST2]

        self.system.delete(DEVICE_TEST)
        assert self.system.config == [DEVICE_TEST2]

        self.system.delete(DEVICE_TEST2)
        assert self.system.config == []

    def test_reset(self):
        self.system.load()

        assert self.system.config == []

        self.system.save(DEVICE_TEST)
        self.system.save(DEVICE_TEST2)
        assert self.system.config == [DEVICE_TEST, DEVICE_TEST2]

        self.system.reset()
        assert self.system.config == []

    def setUp(self):
        self.system = BaseSystem()
        self.system.get_mqtt_server = MQTT_HOST_MOCK
        self.system.get_mqtt_login = MQTT_LOGIN_MOCK

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        cls.config_backup = get_default_configuration_for(CUBIE_SYSTEM)

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_SYSTEM, cls.config_backup)
        if cls.mqtt_server_process:
            cls.mqtt_server_process.terminate()
            cls.mqtt_server_process.communicate()
