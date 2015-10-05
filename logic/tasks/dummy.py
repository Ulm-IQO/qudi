# -*- coding: utf-8 -*-

from logic.generic_task import InterruptableTask
import time

class Task(InterruptableTask):

    def __init__(self, name, runner):
        super().__init__(name, runner)
        print('Task {} added!'.format(self.name))

    def startTask(self):
        print('Start')

    def runTaskStep(self):
        time.sleep(0.1)
        print('one task step')
        return True

    def pauseTask(self):
        time.sleep(1)
        print('paused task')

    def resumeTask(self):
        time.sleep(1)
        print('resumed task')

    def cleanupTask(self):
        print('task cleaned up')

    def checkExtraStartPrerequisites(self):
        print('things neede for task to start')
        return True

    def checkExtraPausePrerequisites(self):
        print('things neede for task to pause')
        return True

