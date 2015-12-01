# -*- coding: utf-8 -*-

from logic.generic_task import InterruptableTask
import time

class Task(InterruptableTask):

    def __init__(self, name, runner, references, config):
        super().__init__(name, runner, references, config)
        print('Task {} added!'.format(self.name))
        self.ctr = 0

    def startTask(self):
        print('Start')
        self.ctr = 0

    def runTaskStep(self):
        time.sleep(0.1)
        print('one task step', self.ctr)
        self.ctr += 1
        self._result = '{} lines printed!'.format(self.ctr)
        return self.ctr < 50

    def pauseTask(self):
        time.sleep(1)
        print('paused task')

    def resumeTask(self):
        time.sleep(1)
        print('resumed task')

    def cleanupTask(self):
        print(self._result)
        print('task cleaned up')

    def checkExtraStartPrerequisites(self):
        print('things neede for task to start')
        return True

    def checkExtraPausePrerequisites(self):
        print('things neede for task to pause')
        return True

