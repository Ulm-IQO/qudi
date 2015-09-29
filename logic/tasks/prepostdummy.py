# -*- coding: utf-8 -*-

from logic.generic_task import PrePostTask
import time

class Task(PrePostTask):

    def __init__(self, name):
        super().__init__(name)
    
    def preExecute(self):
        time.sleep(1)
        print('pre action of task {}'.format(self.name))

    def preExecute(self):
        time.sleep(1)
        print('post action of task {}'.format(self.name))

