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

Copyright (C) 2015-2016 Jan M. Binder jan.binder@uni-ulm.de
"""
from logic.generic_task import PrePostTask
import time

class Task(PrePostTask):

    def __init__(self, name, runner, references, config):
        super().__init__(name, runner, references, config)
        print('PrePost init task {}'.format(name))
        print(self.config)
    
    def preExecute(self):
        time.sleep(1)
        print('pre action of task {}'.format(self.name))

    def postExecute(self):
        time.sleep(1)
        print('post action of task {}'.format(self.name))

