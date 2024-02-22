import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock

from serial import Serial

from common import CUBIE_CORE
from common.python import set_default_configuration, get_default_configuration_for
from system.sonar_system import SonarSystem, DEFAULT_UPDATE_INTERVAL, DEFAULT_OFFSET, DEFAULT_TRIGGER_OFFSET, \
    DEFAULT_MAXIMAL_DISTANCE, DEFAULT_DISTANCE_OFFSET
from test_common import check_mqtt_server, AUTHENTICATION_MOCK

DEVICE_TEST = {"id": "Test", "value": 1300}
DEVICE_TEST2 = {"id": "Test2", "value": 2774}


class TestSonarSystem(TestCase):
    config_backup = None
    mqtt_server_process = subprocess.Popen
    system = None

    def test_init(self):
        assert not self.system.communicator
        self.system.init()
        time.sleep(1)

        assert self.system.update_interval == DEFAULT_UPDATE_INTERVAL
        assert self.system.offset == DEFAULT_OFFSET
        assert self.system.offset_trigger == DEFAULT_TRIGGER_OFFSET
        assert self.system.maximal_distance != DEFAULT_MAXIMAL_DISTANCE
        assert self.system.maximal_distance == self.system.config[0]['maximal_distance']
        assert self.system.offset_distance == DEFAULT_DISTANCE_OFFSET

    def test_shutdown(self):
        self.system.init()
        time.sleep(1)

        assert self.system.mqtt_client.mqtt_client.is_connected()

        self.system.set_availability = MagicMock()
        self.system.shutdown()
        self.system.set_availability.assert_called_once()
        assert not self.system.mqtt_client.mqtt_client.is_connected()

    def test_action(self):
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.publish = MagicMock()
        self.system.action(DEVICE_TEST)
        self.system.mqtt_client.publish.assert_called()

    def test_update(self):
        self.system.init()
        time.sleep(1)
        self.system.set_availability = MagicMock()
        self.system.communicator = MagicMock()
        self.system.communicator.in_waiting = 15

        self.system.communicator.read = MagicMock(side_effect=["Gap=333mm"])
        temp_distance = self.system.distance
        self.system.update()
        assert self.system.distance != temp_distance
        self.system.set_availability.assert_called_once()

        self.system.last_update = time.time() - 1000

        self.system.communicator.read = MagicMock(side_effect=["Gap=653mm"])
        temp_distance = self.system.distance
        self.system.update()
        assert self.system.distance != temp_distance
        self.system.set_availability.assert_called_with(True)

        self.system.last_update = time.time() - 1000
        self.system.communicator.read = MagicMock(side_effect=["Gap=87mm"])
        temp_distance = self.system.distance
        self.system.update()
        assert self.system.distance == temp_distance
        self.system.set_availability.assert_called_with(True)

        self.system.communicator.read = MagicMock(side_effect=["Gap=411mm"])
        temp_distance = self.system.distance
        self.system.update()
        assert self.system.distance == temp_distance
        self.system.set_availability.assert_called_with(True)

        self.system.last_update = time.time() - 1000
        self.system.communicator.read = MagicMock(side_effect=["Gap=411mm"])
        temp_distance = self.system.distance
        self.system.update()
        assert self.system.distance != temp_distance
        self.system.set_availability.assert_called_with(True)

    def test_announce(self):
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client = MagicMock()
        self.system.announce()
        self.system.mqtt_client.publish.assert_called_once()
        self.system.mqtt_client.subscribe.assert_called_once()

    def setUp(self):
        self.system = SonarSystem()
        self.system.get_mqtt_data = AUTHENTICATION_MOCK

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        cls.config_backup = get_default_configuration_for(CUBIE_CORE)
        cls.mqtt_server_process = check_mqtt_server()

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_CORE, cls.config_backup)
        if cls.mqtt_server_process:
            cls.mqtt_server_process.terminate()
            cls.mqtt_server_process.communicate()
