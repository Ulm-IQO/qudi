# -*- coding: utf-8 -*-
"""
Confocal-refocus task.

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
        print('Task {} added!'.format(self.name))

    def startTask(self):
        """ Get position from scanning device and do the refocus """
        pos = self.ref['optimizer']._scanning_device.get_scanner_position()
        self.ref['optimizer'].start_refocus(pos, 'task')
        # self.ref['optimizer'].start_refocus(caller_tag='task')

    def runTaskStep(self):
        """ Wait for refocus to finish. """
        time.sleep(0.1)
        return self.ref['optimizer'].isstate('locked')

    def pauseTask(self):
        """ pausing a refocus is forbidden """
        pass

    def resumeTask(self):
        """ pausing a refocus is forbidden """
        pass

    def cleanupTask(self):
        """ nothing to clean up, optimizer can do that by itself """

    def checkExtraStartPrerequisites(self):
        """ Check whether anything we need is locked. """
        print('things needed for task to start')
        return (
            not self.ref['optimizer']._scanning_device.isstate('locked')
            and not self.ref['optimizer'].isstate('locked')
            )

    def checkExtraPausePrerequisites(self):
        """ pausing a refocus is forbidden """
        return False

