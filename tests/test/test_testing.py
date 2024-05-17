import time
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock

from system.victron_system import SERVICES


class TestTesting(TestCase):

    def test_the_testing(self):
        msg = MagicMock()
        topic = PropertyMock(side_effect=SERVICES)
        type(msg).topic = topic
        for service in SERVICES:
            assert msg.topic == service
