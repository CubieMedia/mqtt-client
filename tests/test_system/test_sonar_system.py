import logging
import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock

from common import CUBIE_SYSTEM, CUBIE_SONAR
from common.python import set_default_configuration, get_default_configuration_for
from system.sonar_system import SonarSystem, DEFAULT_UPDATE_INTERVAL, DEFAULT_OFFSET, DEFAULT_TRIGGER_OFFSET, \
    DEFAULT_MAXIMAL_DISTANCE, DEFAULT_DISTANCE_OFFSET
from test_common import check_mqtt_server, MQTT_HOST_MOCK

DEVICE_TEST = {"id": "Test", "value": 1300}


class TestSonarSystem(TestCase):
    config_backup = None
    sonar_backup = None
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
        assert self.system.distance_offset == DEFAULT_DISTANCE_OFFSET

    def test_shutdown(self):
        self.test_init()

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

    def setUp(self):
        self.system = SonarSystem()
        self.system.get_mqtt_server = MQTT_HOST_MOCK

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)
        cls.config_backup = get_default_configuration_for(CUBIE_SYSTEM)
        cls.sonar_backup = get_default_configuration_for(CUBIE_SONAR)
        cls.mqtt_server_process = check_mqtt_server()

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_SYSTEM, cls.config_backup)
        set_default_configuration(CUBIE_SONAR, cls.sonar_backup)
        if cls.mqtt_server_process:
            cls.mqtt_server_process.terminate()
            cls.mqtt_server_process.communicate()
