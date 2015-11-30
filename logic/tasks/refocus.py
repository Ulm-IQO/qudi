# -*- coding: utf-8 -*-

from logic.generic_task import InterruptableTask

class Task(InterruptableTask):

    def __init__(self, name, runner, references, config):
        super().__init__(name, runner, references, config)
        print('Task {} added!'.format(self.name))

    def startTask(self):
        self.ref['optimizer'].start_refocus(self.config['initial'], 'task')

    def runTaskStep(self):
        pass

    def pauseTask(self):
        pass

    def resumeTask(self):
        pass

    def cleanupTask(self):
        pass
