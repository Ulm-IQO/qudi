# -*- coding: utf-8 -*-

from logic.generic_task import InterruptableTask
import time

class Task(InterruptableTask):

    def __init__(self, name, runner, references, config):
        super().__init__(name, runner, references, config)
        print('Task {} added!'.format(self.name))

    def startTask(self):
        pos = self.ref['optimizer']._scanning_device.get_scanner_position()
        self.ref['optimizer'].start_refocus(pos, 'task')

    def runTaskStep(self):
        time.sleep(0.1)
        return self.ref['optimizer'].isstate('locked')

    def pauseTask(self):
        pass

    def resumeTask(self):
        pass

    def cleanupTask(self):
        print("cleanup")

    def checkExtraStartPrerequisites(self):
        print('things neede for task to start')
        return not self.ref['optimizer'].isstate('locked')

    def checkExtraPausePrerequisites(self):
        print('things neede for task to pause')
        return True

