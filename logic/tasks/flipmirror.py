# -*- coding: utf-8 -*-

from logic.generic_task import InterruptableTask

class Task(InterruptableTask):

    def __init__(self, name, runner, **kwargs):
        super().__init__(name, runner, **kwargs)
        print('Task {} added!'.format(self.name))

    def startTask(self):
        pass

    def runTaskStep(self):
        pass

    def pauseTask(self):
        pass

    def resumeTask(self):
        pass

    def cleanupTask(self):
        pass
