# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interfuse between single shot logic and fastcomtec hardware.

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


"""
An interfuse file is indented to fuse/combine a logic with a hardware, which
was not indented to be used with the logic. The interfuse file extend the
ability of a hardware file by converting the logic calls (from a different
interface) to the interface commands, which suits the hardware.
In order to be addressed by the (magnet) logic it should inherit the (magnet)
interface, and given the fact that it will convert a magnet logic call to a
motor hardware call, that 'interfuse' file has to stick to the interfaces
methods of the motor interface.

Reimplement each call from the magnet interface and use only the motor interface
command to talk to a xyz motor hardware and a rotational motor hardware.
"""

import numpy as np
from core.util.network import netobtain
from core.module import Connector
from logic.generic_logic import GenericLogic
from interface.single_shot_interface import SingleShotInterface


class FastcomtecSSRCounterInterfuse(GenericLogic, SingleShotInterface):

    _modclass = 'FastcomtecSingleShotInterfuse'
    _modtype = 'interfuse'

    # declare connectors, here you can see the interfuse action: the in
    # connector will cope a motor hardware, that means a motor device can
    # connect to the in connector of the logic.
    #FIXME:
    fastcomtec = Connector(interface='MotorInterface')
    pulsedmeasurementlogic = Connector(interface='MotorInterface')



    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._fastcomtec = self.fastcomtec()
        self._pulsedmeasurementlogic = self.pulsedmeasurementlogic()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def get_constraints(self):
        """ Retrieve the hardware constrains from the magnet driving device.

        @return dict: dict with constraints for the magnet hardware. These
                      constraints will be passed via the logic to the GUI so
                      that proper display elements with boundary conditions
                      could be made.
        """
        constraints = self._fastcomtec.get_constraints()
        return constraints


    def configure_ssr_counter(self, counts_per_readout, countlength):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        A smart idea would be to ask the position after the movement.
        @return dict pos: dictionary with changed axis and positions
        """
        self._fastcomtec.configure_ssr_counter(counts_per_readout, countlength)
        return




    def get_status(self):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """
        status = self._fastcomtec.get_status()
        return status



    def start_measure(self):
        """ Start the fast counter. """
        status = self._fastcomtec.start_measure()
        return status


    def stop_measure(self):
        """ Stop the fast counter. """
        status = self._fastcomtec.stop_measure()
        return status


    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        status = self._fastcomtec.pause_measure()
        return status


    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        status = self._fastcomtec.continue_measure()
        return status




    def get_data_trace(self, normalized):
        """ Polls the current timetrace data from the fastcomtec.

        Return value is a numpy array (dtype = int64).
        Will return a 1D-numpy-array
        """

        raw_data = netobtain(self._fastcomtec.get_data_trace())

        # remove all zeros
        data_size = np.where(~raw_data.any(axis=1))[0]
        ssr_data = np.delete(raw_data, data_size, 0)
        self.raw_data = ssr_data

        if normalized:
            # FIXME: here it is important that one laser pulse is on one side respectively
            data_width = self.raw_data.shape[1]
            raw_data1 = self.raw_data[:, :int(data_width / 2)]
            raw_data2 = self.raw_data[:, int(data_width / 2):]
            return_dict1 = self._pulsedmeasurementlogic._pulseextractor.extract_laser_pulses(raw_data1)
            laser1 = return_dict1['laser_counts_arr']
            return_dict2 = self._pulsedmeasurementlogic._pulseextractor.extract_laser_pulses(raw_data2)
            laser2 = return_dict2['laser_counts_arr']
            self.laser_data = [laser1, laser2]
            if laser1.any() and laser2.any():
                tmp_signal1, tmp_error1 = self._pulsedmeasurementlogic._pulseanalyzer.analyse_laser_pulses(laser1)
                tmp_signal2, tmp_error2 = self._pulsedmeasurementlogic._pulseanalyzer.analyse_laser_pulses(laser2)
                tmp_signal = (tmp_signal1 - tmp_signal2) / (tmp_signal1 + tmp_signal2)
            else:
                tmp_signal = np.zeros(self.laser_data.shape[0])
        else:
            return_dict = self._pulsedmeasurementlogic._pulseextractor.extract_laser_pulses(self.raw_data)
            self.laser_data = return_dict['laser_counts_arr']
            # analyze pulses and get data points for signal array.
            if self.laser_data.any():
                tmp_signal, tmp_error = self._pulsedmeasurementlogic._pulseanalyzer.analyse_laser_pulses(
                    self.laser_data)
                tmp_signal = tmp_signal - np.mean(tmp_signal)
            else:
                tmp_signal = np.zeros(self.laser_data.shape[0])
                # get rid of the last point since it is measured with less redouts
        return tmp_signal[:-1]






