import time
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from system.victron_system import SERVICE_LIST


class TestTesting(TestCase):

    def test_the_testing(self):
        msg = MagicMock()
        topic = PropertyMock(side_effect=SERVICE_LIST)
        type(msg).topic = topic
        for service in SERVICE_LIST:
            assert msg.topic == service
