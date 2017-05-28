from unittest.mock import Mock, MagicMock
from hardware.attocube_stepper import AttoCubeStepper
from core.manager import Manager
import telnetlib


class TestAttoCubeStepper:
    def setup(self):
        print("TestAttoCubeStepper:setup() before each test method")

    def teardown(self):
        print("TestAttoCubeStepper:teardown() after each test method")

    @classmethod
    def setup_class(cls):
        print("setup_class() before any methods in this class")

    @classmethod
    def teardown_class(cls):
        print("teardown_class() after any methods in this class")

    def test_send_cmd(self):
        stepper = AttoCubeStepper(manager=MagicMock(Manager), name="Name")
        stepper.connected = True
        stepper.tn = Mock(telnetlib.Telnet)





        stepper.tn.read_eager.side_effect = ["Junk", "mode = gnd\r\nOK\r\n"]
        assert 0 == stepper._send_cmd("getm 1")
        assert 2 == stepper.tn.read_eager.call_count

        stepper.tn.read_eager.side_effect = ["Junk", "ERROR\r\n"]
        assert -1 == stepper._send_cmd("getm1")

        stepper.tn.read_eager.side_effect = ["Junk", ""]
        assert -1 == stepper._send_cmd("Blode Komando")

        stepper.tn.read_eager.side_effect = ["Junk", "mode = gnd\r\nOK\r\n"]
        stepper.tn.write.side_effect= OSError("Attocube is not avaliable anymore")
        assert -1 == stepper._send_cmd("getm 1")