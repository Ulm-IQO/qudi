# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware module for the FPGA based fast counter.

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

Copyright (C) 2016 Nikolas Tomek nikolas.tomek@uni-ulm.de
Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""

import numpy as np
import struct
import os

from interface.fast_counter_interface import FastCounterInterface
from core.base import Base
import thirdparty.opal_kelly.ok64 as ok


class FastCounterFPGAQO(Base, FastCounterInterface):
    """ unstable: Nikolas Tomek
        This is the hardware class for the Spartan-6 (Opal Kelly XEM6310) FPGA
        based fast counter.
        The command reference for the communicating via the OpalKelly Frontend
        can be looked up here:

            https://library.opalkelly.com/library/FrontPanelAPI/index.html

        The Frontpanel is basically a C++ interface, where a wrapper was used
        (SWIG) to access the dll library. Be aware that the wrapper is specified
        for a specific version of python (here python 3.4), and it is not
        guaranteed to be working with other versions.
    """
    _modclass = 'FastCounterFPGAQO'
    _modtype = 'hardware'
    # declare connectors
    _out = {'fastcounter': 'FastCounterInterface'}

    def __init__(self, manager, name, config={}, **kwargs):
        callback_dict = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, callback_dict, **kwargs)

    def activation(self, e):
        """ Connect and configure the access to the FPGA.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.
        """

        config = self.getConfiguration()

        if 'fpgacounter_serial' in config.keys():
            self._serial = config['fpgacounter_serial']
        else:
            self.logMsg('No parameter "fpgacounter_serial" specified  in the '
                        'config! Set the serial number for the currently used '
                        'fpga counter!\n'
                        'Open the Opal Kelly Frontpanel to obtain the serial '
                        'number of the connected FPGA.\n'
                        'Do not forget to close the Frontpanel before starting '
                        'the QuDi program.', msgType='error')

        if 'fpga_type' in config.keys():
            self._fpga_type = config['fpga_type']
        else:
            self._fpga_type = 'XEM6310_LX150'
            self.logMsg('No parameter "fpga_type" specified in the config!\n'
                        'Possible types are "XEM6310_LX150" or '
                        '"XEM6310_LX45".\n'
                        'Taking the type "{0}" as '
                        'default.'.format(self._fpga_type),
                        msgType='warning')

        # Create an instance of the Opal Kelly FrontPanel. The Frontpanel is a
        # c dll which was wrapped with SWIG for Windows type systems to be
        # accessed with python 3.4. You have to ensure to use the python 3.4
        # version to be able to run the Frontpanel wrapper:

        self._fpga = ok.FrontPanel()
        # fast counter state
        self.statusvar = -1
        # fast counter parameters to be configured. Default values.
        self._binwidth = 1              # number of elementary bins to be put
                                        # together in one bigger bin
        self._gate_length_bins = 8192   # number of bins in one gate (max 8192)
        self._number_of_gates = 1       # number of gates in the pulse sequence
                                        # (max 2048)
        self._histogram_size = 1*8192   # histogram size in bins to tell the
                                        # FPGA (integer multiple of 8192)

        self._old_data = None           # histogram to be added to the current
                                        # data, i.e. after an overflow on the
                                        # FPGA.
        self._overflown = False         # overflow indicator
        self.count_data = None

        self._internal_clock_hz = 950e6 # that is a fixed number, 950MHz
        # connect to the FPGA module
        self._connect()

    def deactivation(self, e):
        """ Deactivate the FPGA.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self.stop_measure()
        self.statusvar = 0
        del self._fpga

    def _connect(self):
        """ Connect host PC to FPGA module with the specified serial number. """

        # check if a FPGA is connected to this host PC. That method is used to
        # determine also how many devices are available.
        if not self._fpga.GetDeviceCount():
            self.logMsg('No FPGA connected to host PC or FrontPanel.exe is '
                        'running.', msgType='error')
            return -1

        # open a connection to the FPGA with the specified serial number
        self._fpga.OpenBySerial(self._serial)

        # upload the proper fast counter configuration bitfile to the FPGA
        bitfile_name = 'fastcounter_' + self._fpga_type + '.bit'

        # Load on the FPGA a configuration file (bit file).
        self._fpga.ConfigureFPGA(os.path.join(self.get_main_dir(),
                                                'thirdparty',
                                                'qo_fpga',
                                                bitfile_name))

        # Check if the upload was successful and the Opal Kelly FrontPanel is
        # enabled on the FPGA
        if not self._fpga.IsFrontPanelEnabled():
            self.logMsg('Opal Kelly FrontPanel is not enabled in FPGA',
                        msgType='error')
            self.statusvar = -1
            return -1
        else:
            # Put the fast counter logic and its clock into reset mode
            self._fpga.SetWireInValue(0x00, 0xC0000000)
            self._fpga.UpdateWireIns()
            self.statusvar = 0
        return 0

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
        constraints['hardware_binwidth_list'] = [1/950e6]

        #TODO: think maybe about a software_binwidth_list, which will
        #      postprocess the obtained counts. These bins must be integer
        #      multiples of the current hardware_binwidth

        return constraints

    def configure(self, bin_width_s, record_length_s, number_of_gates=0):
        """ Configuration of the fast counter.

        @param float bin_width_s: Length of a single time bin in the time trace
                                  histogram in seconds.
        @param float record_length_s: Total length of the timetrace/each single
                                      gate in seconds.
        @param int number_of_gates: optional, number of gates in the pulse
                                    sequence. Ignore for not gated counter.

        @return tuple(binwidth_s, gate_length_s, number_of_gates):
                    binwidth_s: float the actual set binwidth in seconds
                    gate_length_s: the actual set gate length in seconds
                    number_of_gates: the number of gated, which are accepted
        """

        # set class variables
        self._binwidth = int(np.rint(bin_width_s * self._internal_clock_hz))

        # calculate the actual binwidth depending on the internal clock:
        binwidth_s = self._binwidth / self._internal_clock_hz

        self._gate_length_bins = int(np.rint(record_length_s / bin_width_s))
        gate_length_s = self._gate_length_bins * binwidth_s

        self._number_of_gates = number_of_gates
        self._histogram_size = number_of_gates * 8192

        # reset overflow indicator
        self._overflown = False

        # release the fast counter clock but leave the logic in reset mode
        # set histogram size in the hardware
        self._fpga.SetWireInValue(0x00, 0x40000000 + self._histogram_size)
        self._fpga.UpdateWireIns()
        self.statusvar = 1
        return binwidth_s, gate_length_s, number_of_gates

    def start_measure(self):
        """ Start the fast counter. """

        # initialize the data array
        self.count_data = np.zeros([self._number_of_gates,
                                    self._gate_length_bins])
        # reset overflow indicator
        self._overflown = False
        # Release all reset states and start the counter.
        # Keep the histogram size.
        self._fpga.SetWireInValue(0x00, self._histogram_size)
        self._fpga.UpdateWireIns()
        self.statusvar = 2
        return 0

    def get_data_trace(self):
        """ Polls the current timetrace data from the fast counter.

        @return numpy.array: 2 dimensional array of dtype = int64. This counter
                             is gated the the return array has the following
                             shape:
                                returnarray[gate_index, timebin_index]

        The binning, specified by calling configure() in forehand, must be taken
        care of in this hardware class. A possible overflow of the histogram
        bins must be caught here and taken care of.
        """
        # initialize the read buffer for the USB transfer.
        # one timebin of the data to read is 32 bit wide and the data is
        # transferred in bytes.

        if self.statusvar != 2:
            self.logMsg('The FPGA is currently not running! The current status '
                        'is: "{0}". The running status would be 2. Start the '
                        'FPGA to get the data_trace of the device. An emtpy '
                        'numpy array[{1},{2}] filled with zeros will be '
                        'returned.'.format(self.statusvar,
                                           self._number_of_gates,
                                           self._gate_length_bins),
                        msgType='error')

            return self.count_data

        data_buffer = bytearray(self._histogram_size*4)
        # check if the timetagger had an overflow.
        self._fpga.UpdateWireOuts()
        flags = self._fpga.GetWireOutValue(0x20)
        if flags != 0:
            # send acknowledge signal to FPGA
            self._fpga.SetWireInValue(0x00, 0x08000000 + self._histogram_size)
            self._fpga.UpdateWireIns()
            self._fpga.SetWireInValue(0x00, self._histogram_size)
            self._fpga.UpdateWireIns()

            # save latest count data into a new class variable to preserve it
            self._old_data = self.count_data.copy()
            self._overflown = True

        # trigger the data read in the FPGA
        self._fpga.SetWireInValue(0x00, 0x20000000 + self._histogram_size)
        self._fpga.UpdateWireIns()
        self._fpga.SetWireInValue(0x00, self._histogram_size)
        self._fpga.UpdateWireIns()

        # read data from the FPGA
        self._fpga.ReadFromBlockPipeOut(0xA0, 1024, data_buffer)

        # encode the bytearray data into 32-bit integers
        buffer_encode = np.array(struct.unpack("<"+"L"*self._histogram_size,
                                 data_buffer))

        # bin the data according to the specified bin width
        if self._binwidth != 1:
            buffer_encode = buffer_encode[:(buffer_encode.size //
                            self._binwidth) * self._binwidth].reshape(-1,
                                self._binwidth).sum(axis=1)

        # reshape the data array into the 2D output array
        self.count_data = buffer_encode.reshape(self._number_of_gates, -1)[:, 0:self._gate_length_bins]
        if self._overflown:
            self.count_data = np.add(self.count_data, self._old_data)
        return self.count_data

    def stop_measure(self):
        """ Stop the fast counter. """

        # put the fast counter logic into reset state
        self._fpga.SetWireInValue(0x00, 0x40000000 + self._histogram_size)
        self._fpga.UpdateWireIns()
        # reset overflow indicator
        self._overflown = False
        self.statusvar = 1
        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        # set the pause state in the FPGA
        self._fpga.SetWireInValue(0x00, 0x10000000 + self._histogram_size)
        self._fpga.UpdateWireIns()
        self.statusvar = 3
        return 0

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        # exit the pause state in the FPGA
        self._fpga.SetWireInValue(0x00, self._histogram_size)
        self._fpga.UpdateWireIns()
        self.statusvar = 2
        return 0

    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """
        return True

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return float: current length of a single bin in seconds (seconds/bin)
        """
        width_in_seconds = self._binwidth * 1e-6/950
        return width_in_seconds

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
