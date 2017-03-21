# -*- coding: utf-8 -*-
"""
Dummy preposttask

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
import time

class Task(PrePostTask):
    """ Dummy thask that does nothing before and after a different task has run. """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('PrePost init task {0}'.format(name))
        print(self.config)

    def preExecute(self):
        """ Do nothing befoer other task runs
        """
        time.sleep(1)
        print('pre action of task {0}'.format(self.name))

    def postExecute(self):
        """ Do more nothing after other task has finished running
        """
        time.sleep(1)
        print('post action of task {0}'.format(self.name))

