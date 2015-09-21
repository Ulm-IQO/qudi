# -*- coding: utf-8 -*-

from logic.generic_task import InterruptibleTask

class Task(InterruptibleTask):

    def __init__(self):
        super().__init__('Refocus')
        print('Task {} added!'.format(self.name))

    def startTasklet(self):
        pass

    def runTaskletStep(self):
        pass

    def pauseTasklet(self):
        pass

    def resumeTasklet(self):
        pass

    def cleanupTasklet(self):
        pass
