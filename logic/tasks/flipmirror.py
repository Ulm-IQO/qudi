# -*- coding: utf-8 -*-
"""
Flipmirror preposttask

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from logic.generic_task import PrePostTask

class Task(PrePostTask):
    """ A task to flip a switch/mirror/etc before and after another task
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))

    def preExecute(self):
        """ Flip in one direction before the other task executes
        """
        if ('switchlogic' in self.ref
            and 'sequence' in self.config):
                logic = self.ref['switchlogic']
                for element in self.config['sequence']:
                    if element[2]:
                        logic.switches[element[0]][element[1]].switchOn(element[1])
                    else:
                        logic.switches[element[0]][element[1]].switchOff(element[1])
        else:
            self.log.error('No switching sequence configured for pre/post '
                    'task {}'.format(self.name))


    def postExecute(self):
        """ Flip in the other direction after the other task has finished
        """
        if ('switchlogic' in self.ref
            and 'sequence' in self.config):
                logic = self.ref['switchlogic']
                for element in reversed(self.config['sequence']):
                    if element[2]:
                        logic.switches[element[0]][element[1]].switchOff(element[1])
                    else:
                        logic.switches[element[0]][element[1]].switchOn(element[1])
        else:
            self.log.error('No switching sequence configured for pre/post '
                    'task {}'.format(self.name))


