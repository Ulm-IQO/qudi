# -*- coding: utf-8 -*-

from logic.generic_task import PrePostTask

class Task(PrePostTask):

    def __init__(self, name, runner, references, config):
        super().__init__(name, runner, references, config)
        print('Task {} added!'.format(self.name))

    def preExecute(self):
        if ('switchlogic' in self.ref
            and 'sequence' in self.config):
                logic = self.ref['switchlogic']
                for element in self.config['sequence']:
                    if element[2]:
                        logic.switches[element[0]][element[1]].switchOn(element[1])
                    else:
                        logic.switches[element[0]][element[1]].switchOff(element[1])
        else:
            self.runner.logMsg('No switching sequence configured for pre/post task {}'.format(self.name), msgType='error')


    def postExecute(self):
        if ('switchlogic' in self.ref
            and 'sequence' in self.config):
                logic = self.ref['switchlogic']
                for element in reversed(self.config['sequence']):
                    if element[2]:
                        logic.switches[element[0]][element[1]].switchOff(element[1])
                    else:
                        logic.switches[element[0]][element[1]].switchOn(element[1])
        else:
            self.runner.logMsg('No switching sequence configured for pre/post task {}'.format(self.name), msgType='error')


