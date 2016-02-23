# -*- coding: utf-8 -*-

from logic.generic_task import InterruptableTask
import time

class Task(InterruptableTask):

    def __init__(self, name, runner, references, config):
        super().__init__(name, runner, references, config)
        print('Task {} added!'.format(self.name))

    def startTask(self):
        """ Get position from scanning device and do the refocus """
        pos = self.ref['optimizer']._scanning_device.get_scanner_position()
        self.ref['optimizer'].start_refocus(pos, 'task')

    def runTaskStep(self):
        """ Wait for refocus to finish. """
        time.sleep(0.1)
        return self.ref['optimizer'].isstate('locked')

    def pauseTask(self):
        """ pausing a refocus is forbidden """
        pass

    def resumeTask(self):
        """ pausing a refocus is forbidden """
        pass

    def cleanupTask(self):
        """ nothing to clean up, optimizer can do that by itself """

    def checkExtraStartPrerequisites(self):
        """ Check whether anything we need is locked. """
        print('things needed for task to start')
        return (
            not self.ref['optimizer']._scanning_device.isstate('locked')
            and not self.ref['optimizer'].isstate('locked')
            )

    def checkExtraPausePrerequisites(self):
        """ pausing a refocus is forbidden """
        return False

