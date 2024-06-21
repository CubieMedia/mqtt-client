import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from common import CUBIE_SYSTEM, CUBIE_VICTRON
from common.homeassistant import VICTRON_MQTT_TOPIC
from common.python import set_default_configuration, get_default_configuration_for
from system.victron_system import VictronSystem, SERVICES, VICTRON_WRITE_TOPIC, victron_mqtt_topics
from test_common import check_mqtt_server, MQTT_HOST_MOCK, MQTT_LOGIN_MOCK

SERVICE_PAYLOAD = {'battery_power': 377, 'battery_soc': 33, 'battery_charged': 0, 'battery_discharged': 0,
                   'grid_exported': 0, 'grid_imported': 0, 'grid_lost_alarm': False, 'allow_charge': 1,
                   'allow_discharge': 1}
SERVICE_RESPONSE = {'battery_power': 377, 'battery_soc': 33, 'battery_charged': 0, 'battery_discharged': 0,
                    'grid_exported': 0, 'grid_imported': 0, 'grid_lost_alarm': False, 'allow_charge': '{"value": 80}',
                    'allow_discharge': '{"value": -1}'}
VICTRON_MESSAGE = [b'{"value": 377}', b'{"value": 33}', b'{"value": 0}', b'{"value": 0}',
                   b'{"value": 0}',
                   b'{"value": 0}', b'{"value": false}', b'{"value": 80}', b'{"value": -1}']


class TestVictronSystem(TestCase):
    config_backup = None
    victron_backup = None
    mqtt_server_process = subprocess.Popen
    system = None

    def test_action(self):
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.publish = MagicMock()
        for topic in SERVICES:
            device = {topic: SERVICE_PAYLOAD[topic]}
            self.system.action(device)
            self.system.mqtt_client.publish.assert_called_once()
            self.system.mqtt_client.publish.reset_mock()

    def test_send(self):
        self.system.init()
        time.sleep(1)

        self.system.victron_mqtt_client.publish = MagicMock()
        topic = 'allow_charge'
        data = {"id": topic,
                "state": str(SERVICE_PAYLOAD[topic])}
        self.system.send(data)
        self.system.victron_mqtt_client.publish.assert_called_with(
            VICTRON_WRITE_TOPIC.format(self.system.victron_system['serial']) + SERVICES[topic][
                VICTRON_MQTT_TOPIC], SERVICE_RESPONSE[topic])

        self.system.victron_mqtt_client.publish = MagicMock()
        topic = 'allow_discharge'
        data = {"id": topic,
                "state": str(SERVICE_PAYLOAD[topic])}
        self.system.send(data)
        self.system.victron_mqtt_client.publish.assert_called_with(
            VICTRON_WRITE_TOPIC.format(self.system.victron_system['serial']) + SERVICES[topic][
                VICTRON_MQTT_TOPIC], SERVICE_RESPONSE[topic])

    def test_init(self):
        self.system.init()
        time.sleep(1)

        assert self.system.mqtt_client.mqtt_client.is_connected()
        assert not self.system.victron_mqtt_client.is_connected()
        assert not self.system._keepalive_thread_event.is_set()

    def test_shutdown(self):
        self.test_init()

        self.system.shutdown()
        time.sleep(1)

        assert not self.system.mqtt_client.mqtt_client.is_connected()
        assert not self.system.victron_mqtt_client.is_connected()
        assert self.system._keepalive_thread_event.is_set()
        assert not self.system._keepalive_thread.is_alive()

    def test_announce(self):
        self.system.init()
        time.sleep(1)

        self.system._keepalive_thread.is_alive()

    def test_load(self):
        assert len(self.system.config) == 0
        self.system.load()
        time.sleep(1)

        assert len(self.system.config) > 0
        assert self.system.victron_system == self.system.config[0]

    def test_connect_victron_system(self):
        self.system.init()
        time.sleep(1)

        self.system.victron_mqtt_client = MagicMock()
        self.system.connect_victron_system()
        self.system.victron_mqtt_client.connect.assert_called_once()
        self.system.victron_mqtt_client.loop_start.assert_called_once()

    def test_on_victron_message(self):
        self.system.init()
        time.sleep(1)

        msg = MagicMock()
        topic = PropertyMock(side_effect=victron_mqtt_topics())
        payload = PropertyMock(side_effect=VICTRON_MESSAGE)

        type(msg).topic = topic
        type(msg).payload = payload

        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system._updated_data['devices']) == 1
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system._updated_data['devices']) == 2
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system._updated_data['devices']) == 3
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system._updated_data['devices']) == 4
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system._updated_data['devices']) == 5

        self.system.update()
        assert len(self.system._updated_data['devices']) == 0

    def test_on_victron_connect(self):
        self.system.init()
        time.sleep(1)

        self.system.victron_mqtt_client = MagicMock()
        self.system.on_victron_connect(self.system.victron_mqtt_client, None, None, 13)
        self.system.victron_mqtt_client.subscribe.assert_not_called()

        self.system.on_victron_connect(self.system.victron_mqtt_client, None, None, 0)
        self.system.victron_mqtt_client.subscribe.assert_called()

    def test_on_victron_disconnect(self):
        self.system.init()
        time.sleep(1)

        self.system.set_availability = MagicMock()
        self.system.on_victron_disconnect(self.system.victron_mqtt_client, None, 13)
        self.system.set_availability.assert_called_once()

        self.system.set_availability.reset_mock()
        self.system.on_victron_disconnect(self.system.victron_mqtt_client, None, 0)
        self.system.set_availability.assert_called_once()

    def test_set_availability(self):
        self.system.mqtt_client = MagicMock()
        self.system.set_availability(False)

        self.system.mqtt_client.publish.assert_called_once()
        self.system.init()
        self.system.mqtt_client = MagicMock()
        self.system.set_availability(False)

        assert len(self.system.mqtt_client.publish.mock_calls) == 2

    def setUp(self):
        self.system = VictronSystem()
        self.system.get_mqtt_server = MQTT_HOST_MOCK
        self.system.get_mqtt_login = MQTT_LOGIN_MOCK

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        cls.config_backup = get_default_configuration_for(CUBIE_SYSTEM)
        cls.victron_backup = get_default_configuration_for(CUBIE_VICTRON)
        cls.mqtt_server_process = check_mqtt_server()

    @classmethod
    def tearDownClass(cls):
        set_default_configuration(CUBIE_SYSTEM, cls.config_backup)
        set_default_configuration(CUBIE_VICTRON, cls.victron_backup)
        if cls.mqtt_server_process:
            cls.mqtt_server_process.terminate()
            cls.mqtt_server_process.communicate()
