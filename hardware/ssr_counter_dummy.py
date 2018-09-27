# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware dummy for fast counting devices.

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

import time
import numpy as np

from core.module import Base, ConfigOption
from interface.single_shot_interface import SingleShotInterface
from random import uniform


class SSRCounterDummy(Base, SingleShotInterface):
    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'ssrcounterinterface'
    _modtype = 'hardware'

    # config option
    trace_path = ConfigOption('load_trace', None)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.statusvar = 0
        self._counts_per_readout = 1000
        self._countlength = 50
        self._count_data = np.ones(3)
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.statusvar = -1
        return

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Fast counting device.

        @return dict: dict with keys being the constraint names as string and
                      items are the definition for the constaints.

         The keys of the returned dictionary are the str name for the constraints
        (which are set in this method).

                    NO OTHER KEYS SHOULD BE INVENTED!

        If you are not sure about the meaning, look in other hardware files to
        get an impression. If still additional constraints are needed, then they
        have to be added to all files containing this interface.

        The items of the keys are again dictionaries which have the generic
        dictionary form:
            {'min': <value>,
             'max': <value>,
             'step': <value>,
             'unit': '<value>'}

        Only the key 'hardware_binwidth_list' differs, since they
        contain the list of possible binwidths.

        If the constraints cannot be set in the fast counting hardware then
        write just zero to each key of the generic dicts.
        Note that there is a difference between float input (0.0) and
        integer input (0), because some logic modules might rely on that
        distinction.

        ALL THE PRESENT KEYS OF THE CONSTRAINTS DICT MUST BE ASSIGNED!
        """

        constraints = dict()

        # the unit of those entries are seconds per bin. In order to get the
        # current binwidth in seonds use the get_binwidth method.
        constraints['hardware_binwidth_list'] = [1/950e6, 2/950e6, 4/950e6, 8/950e6]

        return constraints

    def configure_ssr_counter(self, counts_per_readout, countlength):
        """ Configuration of the fast counter.

        @param int counts_per_readout: optional, number of readouts for one measurement
        @param int countlength: countlength, number of measurements


        @return tuple(counts_per_readout, countlength ):
                    counts_per_readout: optional, number of readouts for one measurement
                    countlength: countlength, number of measurements
        """
        self._counts_per_readout = int(counts_per_readout)
        self._countlength = int(countlength)
        self.statusvar = 1
        return counts_per_readout, countlength


    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        return self.statusvar

    def start_measure(self):
        time.sleep(1)
        self.statusvar = 2
        self._count_data = np.array([])
        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        time.sleep(1)
        self.statusvar = 3
        return 0

    def continue_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        time.sleep(1)
        self.statusvar = 2
        return 0

    def stop_measure(self):
        """ Stop the fast counter. """

        time.sleep(1)
        self.statusvar = 1
        return 0




    def get_data_trace(self):
        """ Polls the current timetrace data from the fast counter.

        Return value is a numpy array (dtype = int64).
        The binning, specified by calling configure() in forehand, must be
        taken care of in this hardware class. A possible overflow of the
        histogram bins must be caught here and taken care of.
        If the counter is NOT GATED it will return a 1D-numpy-array with
            returnarray[timebin_index]
        If the counter is GATED it will return a 2D-numpy-array with
            returnarray[gate_index, timebin_index]
        """

        # include an artificial waiting time
        time.sleep(0.5)
        # add some random data
        for ii in range(10):
            if uniform(-1,1) > 0:
                self._count_data = np.append(self._count_data,np.random.normal(loc = -1., scale = 1.0))
            else:
                self._count_data = np.append(self._count_data,np.random.normal(loc = 1., scale = 1.0))
        return self._count_data

