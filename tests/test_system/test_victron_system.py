import logging
import subprocess
import time
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from system.victron_system import TOPIC_READ_LIST, VictronSystem, SERVICE_LIST, VICTRON_WRITE_TOPIC

SERVICE_PAYLOAD = [377, 33, 0, 0, 0, 0, False, 1, 1]
SERVICE_RESPONSE = [377, 33, 0, 0, 0, 0, False, '{"value": 80}', '{"value": -1}']
VICTRON_MESSAGE = [b'{"value": 377}', b'{"value": 33}', b'{"value": 0}', b'{"value": 0}', b'{"value": 0}',
                   b'{"value": 0}', b'{"value": false}', b'{"value": 80}', b'{"value": -1}']


class TestVictronSystem(TestCase):
    mqtt_server_process = subprocess.Popen
    system = None

    def test_action(self):
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.publish = MagicMock()
        for topic in SERVICE_LIST:
            device = {topic: SERVICE_PAYLOAD[SERVICE_LIST.index(topic)]}
            self.system.action(device)
            self.system.mqtt_client.publish.assert_called_once()
            self.system.mqtt_client.publish.reset_mock()

    def test_send(self):
        self.system.init()
        time.sleep(1)

        self.system.victron_mqtt_client.publish = MagicMock()
        topic = SERVICE_LIST[7]
        data = {"id": topic, "state": str(SERVICE_PAYLOAD[SERVICE_LIST.index(topic)]).encode('UTF-8')}
        self.system.send(data)
        self.system.victron_mqtt_client.publish.assert_called_with(
            VICTRON_WRITE_TOPIC + TOPIC_READ_LIST[SERVICE_LIST.index(topic)],
            SERVICE_RESPONSE[SERVICE_LIST.index(topic)])

        self.system.victron_mqtt_client.publish = MagicMock()
        topic = SERVICE_LIST[8]
        data = {"id": topic, "state": str(SERVICE_PAYLOAD[SERVICE_LIST.index(topic)]).encode('UTF-8')}
        self.system.send(data)
        self.system.victron_mqtt_client.publish.assert_called_with(
            VICTRON_WRITE_TOPIC + TOPIC_READ_LIST[SERVICE_LIST.index(topic)],
            SERVICE_RESPONSE[SERVICE_LIST.index(topic)])

    def test_init(self):
        self.system.mqtt_client.subscribe = MagicMock()
        self.system.init()
        time.sleep(1)

        assert self.system.mqtt_client.mqtt_client.is_connected()
        self.system.mqtt_client.subscribe.assert_called_once()
        assert not self.system.victron_mqtt_client.is_connected()
        assert not self.system.keepalive_thread_event.is_set()

    def test_shutdown(self):
        self.system.init()
        time.sleep(1)

        assert self.system.mqtt_client.mqtt_client.is_connected()
        assert not self.system.keepalive_thread_event.is_set()

        self.system.shutdown()
        time.sleep(1)

        assert not self.system.mqtt_client.mqtt_client.is_connected()
        assert not self.system.victron_mqtt_client.is_connected()
        assert self.system.keepalive_thread_event.is_set()
        assert not self.system.keepalive_thread.is_alive()

    def test_announce(self):
        self.system.set_availability = MagicMock()
        self.system.mqtt_client.subscribe = MagicMock()
        self.system.init()
        time.sleep(1)

        self.system.mqtt_client.subscribe.assert_called_once()
        self.system.set_availability.assert_called()

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
        topic = PropertyMock(side_effect=TOPIC_READ_LIST)
        payload = PropertyMock(side_effect=VICTRON_MESSAGE)

        type(msg).topic = topic
        type(msg).payload = payload

        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system.updated_data['devices']) == 1
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system.updated_data['devices']) == 2
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system.updated_data['devices']) == 3
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system.updated_data['devices']) == 4
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system.updated_data['devices']) == 5
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system.updated_data['devices']) == 6
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system.updated_data['devices']) == 7
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system.updated_data['devices']) == 8
        self.system.on_victron_message(self.system.victron_mqtt_client, None, msg)
        assert len(self.system.updated_data['devices']) == 9

    def test_on_victron_connect(self):
        self.system.init()
        time.sleep(1)

        self.system.victron_mqtt_client = MagicMock()
        self.system.set_availability = MagicMock()
        self.system.on_victron_connect(self.system.victron_mqtt_client, None, None, 13)
        self.system.victron_mqtt_client.subscribe.assert_not_called()
        self.system.set_availability.assert_not_called()

        self.system.on_victron_connect(self.system.victron_mqtt_client, None, None, 0)
        self.system.victron_mqtt_client.subscribe.assert_called()
        self.system.set_availability.assert_called_once()

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

        self.system.mqtt_client.publish.assert_not_called()
        self.system.init()
        self.system.mqtt_client = MagicMock()
        self.system.set_availability(False)

        self.system.mqtt_client.publish.assert_called_once()

    def setUp(self):
        self.system = VictronSystem()
        self.system.get_mqtt_data = MagicMock(return_value=("localhost", None, None))

    def tearDown(self):
        self.system.shutdown()

    @classmethod
    def setUpClass(cls):
        # DODO check mosquitto already running
        try:
            cls.mqtt_server_process = subprocess.Popen("mosquitto")
            time.sleep(1)
        except FileNotFoundError:
            logging.error("could not start mosquitto [sudo apt install mosquitto]")

    @classmethod
    def tearDownClass(cls):
        cls.mqtt_server_process.terminate()
        cls.mqtt_server_process.communicate()
