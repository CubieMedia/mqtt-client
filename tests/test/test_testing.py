import time
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from system.victron_system import SERVICE_LIST


class TestTesting():

    def test_set_availability(self):
        msg = MagicMock()
        topic = PropertyMock(side_effect=SERVICE_LIST)
        type(msg).topic = topic
        assert msg.topic == "Rotz"
