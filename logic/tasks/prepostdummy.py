# -*- coding: utf-8 -*-
"""
Dummy preposttask

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
from logic.generic_task import PrePostTask
import time

class Task(PrePostTask):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('PrePost init task {0}'.format(name))
        print(self.config)

    def preExecute(self):
        time.sleep(1)
        print('pre action of task {0}'.format(self.name))

    def postExecute(self):
        time.sleep(1)
        print('post action of task {0}'.format(self.name))

