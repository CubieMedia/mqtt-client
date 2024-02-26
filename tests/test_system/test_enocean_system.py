import logging
import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock

from enocean.protocol.constants import RORG
from enocean.protocol.packet import Packet

from common import CUBIE_CORE, CUBIE_ENOCEAN
from common.python import set_default_configuration, get_default_configuration_for, get_core_configuration
from system.enocean_system import EnoceanSystem
from test_common import check_mqtt_server, AUTHENTICATION_MOCK

DEVICE_TEST = {"id": "Test", "type": "RPS", "dbm": 67}
DEVICE_TEST_WITH_STATE = {"id": "Test2", "type": "RPS", "dbm": 83, "state": {'a1': 0, 'a2': 0, 'b1': 0, 'b2': 0}}
ACTION_TEST_OFF = {"id": "Test", "type": "RPS", "state": {'a1': 0}, "dbm": 67}
ACTION_TEST_ON = {"id": "Test", "type": "RPS", "state": {'a1': 1}, "dbm": 67}
DATA_TEST = {"ip": "Test", "type": "RPS", "id": 3, "state": b"0"}
PACKET = Packet.create(0x01, RORG.RPS, 0x02, 0x01)


class TestEnoceanSystem(TestCase):
    config_backup = None
    enocean_backup = None
    mqtt_server_process = subprocess.Popen
    system = None

    def test_action(self):
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.publish = MagicMock()
        assert not self.system.action(None)

        self.system.mqtt_client.publish.assert_not_called()

        self.system.mqtt_client.publish = MagicMock()
        assert not self.system.action({})

        self.system.mqtt_client.publish.assert_not_called()

        self.system.mqtt_client.publish = MagicMock()
        self.system.save(DEVICE_TEST)

        action_off = ACTION_TEST_OFF.copy()
        action_off['client_id'] = self.system.client_id
        assert self.system.action(action_off)

        self.system.mqtt_client.publish.assert_called_once()

        self.system.mqtt_client.publish.reset_mock()
        action_on = ACTION_TEST_ON.copy()
        action_on['client_id'] = self.system.client_id
        assert self.system.action(action_on)
        # wait for long press
        time.sleep(1)

        self.system.mqtt_client.publish.assert_called_once()
        # still pressing
        time.sleep(1)
        self.system.mqtt_client.publish.assert_called_once()
        assert self.system.action(action_off)
        assert len(self.system.mqtt_client.publish.mock_calls) == 2

        self.system.mqtt_client.publish.reset_mock()
        # short press
        assert self.system.action(action_on)
        assert self.system.action(action_off)

        self.system.mqtt_client.publish.assert_called_once()
        # waiting for turn off
        time.sleep(1)
        assert len(self.system.mqtt_client.publish.mock_calls) == 2

    def test_update(self):
        self.system.init()
        time.sleep(1)

        self.system.communicator = MagicMock()
        self.system.communicator.receive.get = MagicMock(return_value=PACKET)

        data = self.system.update()
        assert len(data['devices']) > 0

    def test_set_availability(self):
        self.system.init()
        time.sleep(1)
        self.system.save(DEVICE_TEST)

        self.system.mqtt_client = MagicMock()
        self.system.set_availability(False)

        self.system.mqtt_client.publish.assert_called_once()

        self.system.delete(DEVICE_TEST)
        self.system.save(DEVICE_TEST_WITH_STATE)
        self.system.mqtt_client.reset_mock()
        self.system.set_availability(True)

        assert len(self.system.mqtt_client.publish.mock_calls) == 9

    def test_init(self):
        self.system.communicator = MagicMock()
        self.system.load = MagicMock()
        self.system.mqtt_client.publish = MagicMock()
        self.system.core_config = get_core_configuration(self.system.ip_address)
        DEVICE_TEST_WITH_STATE['client_id'] = self.system.client_id
        self.system.save(DEVICE_TEST_WITH_STATE)
        self.system.init()
        time.sleep(1)

        assert self.system.mqtt_client.mqtt_client.is_connected()
        self.system.communicator.start.assert_called_once()
        assert len(self.system.mqtt_client.publish.mock_calls) == 10
        self.system.delete(DEVICE_TEST_WITH_STATE)

    def test_shutdown(self):
        self.system.init()
        time.sleep(1)

        self.system.communicator = MagicMock()
        self.system.shutdown()
        time.sleep(1)

        assert not self.system.mqtt_client.mqtt_client.is_connected()
        self.system.communicator.stop.assert_called_once()

    def test_announce(self):
        self.system.set_availability = MagicMock()
        self.system.communicator = MagicMock()
        self.system.mqtt_client.mqtt_client.subscribe = MagicMock()
        self.system.init()
        time.sleep(1)

        self.system.communicator.start.assert_called_once()
        self.system.mqtt_client.mqtt_client.subscribe.assert_called()
        self.system.set_availability.assert_called()

    def test_save(self):
        self.system.init()
        time.sleep(1)

        self.system.save(DEVICE_TEST)

        assert len(self.system.config) == 1

        self.system.save(DEVICE_TEST_WITH_STATE)

        assert len(self.system.config) == 2

        self.system.delete(DEVICE_TEST)
        self.system.delete(DEVICE_TEST_WITH_STATE)

        assert len(self.system.config) == 0

    def setUp(self):
        self.system = EnoceanSystem()
        self.system.get_mqtt_data = AUTHENTICATION_MOCK

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)
        cls.config_backup = get_default_configuration_for(CUBIE_CORE)
        cls.enocean_backup = get_default_configuration_for(CUBIE_ENOCEAN)
        cls.mqtt_server_process = check_mqtt_server()

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_CORE, cls.config_backup)
        set_default_configuration(CUBIE_ENOCEAN, cls.enocean_backup)
        if cls.mqtt_server_process:
            cls.mqtt_server_process.terminate()
            cls.mqtt_server_process.communicate()
