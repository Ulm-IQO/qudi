from unittest.mock import MagicMock

from hardware.attocube_stepper import AttoCubeStepper
from logic.confocal_stepper_logic import ConfocalStepperLogic
from core.manager import Manager
import numpy as np
from nose.tools import assert_equal


class TestAttoCubeStepperLogic:
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

    def __assert_numpzy_array_equal(self, expected, result):
        assert_equal(len(expected), len(result))
        for i in range(len(expected)):
            assert_equal(expected[i], result[i],
                         "Values on index {} {}!={}".format(i, expected[i], result[i]))

    def test_step_and_count(self):
        manager = MagicMock(Manager)
        config = {}
        config['attocube_axis'] = 1
        confocal_stepper = ConfocalStepperLogic(config=config, manager=manager,
                                                name="Name")
        confocal_stepper.steps_scanner = 20
        confocal_stepper._stepping_device = AttoCubeStepper(config=config, manager=manager,
                                                            name="AttoStepper")
        confocal_stepper._stepping_device = MagicMock(AttoCubeStepper)
        confocal_stepper._counting_device = MagicMock()
        expected = np.zeros(confocal_stepper.steps_scanner)
        confocal_stepper._counting_device.start_counter.return_value = expected
        result = confocal_stepper._step_and_count(axis="x", direction=True)

        self.__assert_numpzy_array_equal(expected, result)
