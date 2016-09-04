# -*- coding: utf-8 -*-
"""
Dummy task for taskrunner.

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
from logic.generic_task import InterruptableTask
import time

class Task(InterruptableTask):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        self.ctr = 0

    def startTask(self):
        print('Start')
        self.ctr = 0

    def runTaskStep(self):
        time.sleep(0.1)
        print('one task step', self.ctr)
        self.ctr += 1
        self._result = '{0} lines printed!'.format(self.ctr)
        return self.ctr < 50

    def pauseTask(self):
        time.sleep(1)
        print('paused task')

    def resumeTask(self):
        time.sleep(1)
        print('resumed task')

    def cleanupTask(self):
        print(self._result)
        print('task cleaned up')

    def checkExtraStartPrerequisites(self):
        print('things needed for task to start')
        return True

    def checkExtraPausePrerequisites(self):
        print('things needed for task to pause')
        return True

