# -*- coding: utf-8 -*-

from logic.generic_task import InterruptibleTask

class Task(InterruptibleTask):

    def __init__(self):
        super().__init__('Refocus')
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
