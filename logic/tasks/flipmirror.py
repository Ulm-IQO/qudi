# -*- coding: utf-8 -*-

from logic.generic_task import PrePostTask

class Task(PrePostTask):

    def __init__(self, name, runner, **kwargs):
        super().__init__(name, runner, **kwargs)
        print('Task {} added!'.format(self.name))


    def preExecute(self):
        if ('modules' in self.kwargs 
            and 'switchlogic' in self.kwargs['modules']
            and 'config' in self.kwargs
            and 'sequence' in self.kwargs['config']):
                logic = self.runner.getModule(self.name, self.kwargs['modules']['switchlogic'])
                for element in self.kwargs['config']['sequence']:
                    logic.switches[element[0]][element[1]].getSwitchState()
        else:
            self.runner.logMsg('No switching sequence configured for pre/post task {}'.format(self.name), msgType='error')

    def postExecute(self):
        pass
