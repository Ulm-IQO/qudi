# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the AWG M8190A device.

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


import visa
import os
import time
import numpy as np
import scipy.interpolate
from fnmatch import fnmatch
from collections import OrderedDict


from core.module import Base
from core.configoption import ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints, SequenceOption, SequenceOrderOption
from core.util.modules import get_home_dir
from core.util.helpers import natural_sort

class AWGM8190A(Base, PulserInterface):
    """ A hardware module for the Keysight M8190A series for generating
        waveforms and sequences thereof.

    Example config for copy-paste:

        myawg:
            module.Class: 'awg.keysight_M8190A.AWGM8190A'
            awg_visa_address: 'TCPIP0::localhost::hislip0::INSTR'
            awg_timeout: 20
            pulsed_file_dir: 'C:/Software/pulsed_files'               # asset directiories should be equal
            assets_storage_path: 'C:/Software/aved_pulsed_assets'     # to the ones in sequencegeneratorlogic
    """
    _modclass = 'awgm8190a'
    _modtype = 'hardware'

    # config options
    _visa_address = ConfigOption(name='awg_visa_address', default='TCPIP0::localhost::hislip0::INSTR', missing='warn')
    _awg_timeout = ConfigOption(name='awg_timeout', default=20, missing='warn')
    _pulsed_file_dir = ConfigOption(name='pulsed_file_dir', default=os.path.join(get_home_dir(), 'pulsed_file_dir'),
                                        missing='warn')
    _assets_storage_path = ConfigOption(name='assets_storage_path', default=os.path.join(get_home_dir(), 'saved_pulsed_assets'),
                                       missing='warn')
    _sample_rate_div = ConfigOption(name='sample_rate_div', default=1, missing='warn')
    _dac_resolution = ConfigOption(name='dac_resolution_bits', default='14', missing='warn')  # 8190 supports 12 (speed) or 14 (precision)
    _dac_amp_mode = 'direct'    # see manual 1.2 'options'

    # physical output channel mapping
    ch_map = {'d_ch1': 'MARK1:SAMP', 'd_ch2': 'MARK2:SAMP', 'd_ch3': 'MARK1:SYNC', 'd_ch4': 'MARK2:SYNC'}
    ch_map_a2d = {'a_ch1': ['d_ch1', 'd_ch3'], 'a_ch2': ['d_ch2', 'd_ch4']}     # corresponding marker channels

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._BRAND = ''
        self._MODEL = ''
        self._SERIALNUMBER = ''
        self._FIRMWARE_VERSION = ''

        self._sequence_mode = False         # set in on_activate()
        self.current_loaded_asset = ''
        self.active_channel = dict()
        self._debug_check_all_commands = False       # for development purpose, might slow down

    def on_activate(self):
        """Initialisation performed during activation of the module.
        """
        self._rm = visa.ResourceManager()

        self._pulsed_file_dir = self._pulsed_file_dir.replace('/', '\\')    # as expected from awg drier
        self._assets_storage_path = self._assets_storage_path.replace('/', '\\')
        self._create_dir(self._pulsed_file_dir)
        self._create_dir(self._assets_storage_path)

        # connect to awg using PyVISA
        try:
            self.awg = self._rm.open_resource(self._visa_address)
            # set timeout by default to 30 sec
            self.awg.timeout = self._awg_timeout * 1000
        except:
            self.awg = None
            self.log.error('VISA address "{0}" not found by the pyVISA resource manager.\nCheck '
                           'the connection by using for example "Keysight Connection Expert".'
                           ''.format(self._visa_address))
            return

        if self.awg is not None:
            mess = self.query('*IDN?').split(',')
            self._BRAND = mess[0]
            self._MODEL = mess[1]
            self._SERIALNUMBER = mess[2]
            self._FIRMWARE_VERSION = mess[3]

            self.log.info('Load the device model "{0}" from "{1}" with the '
                          'serial number "{2}" and the firmware version "{3}" '
                          'successfully.'.format(self._MODEL, self._BRAND,
                                                 self._SERIALNUMBER,
                                                 self._FIRMWARE_VERSION))
            self._sequence_mode  = 'SEQ' in self.query('*OPT?').split(',')
        self._init_device()

    def on_deactivate(self):
        """ Required tasks to be performed during deactivation of the module. """

        try:
            self.awg.close()
            self.connected = False
        except:
            self.log.warning('Closing AWG connection using pyvisa failed.')
        self.log.info('Closed connection to AWG')


    def _init_device(self):
        """ Run those methods during the initialization process."""

        self.reset()

        self.write(':ROSC:SOUR INT') # Chose source for reference clock

        # Sec. 8.22.6 in manual:
        # To prepare your module for arbitrary waveform generation follow these steps:
        # 1. Select one of the direct modes (precision or speed mode) or one of the interpolated modes ((x3, x12, x24 and x48)
        if self._dac_resolution == 12:
            self.write(':TRAC1:DWID WSP')
            self.write(':TRAC2:DWID WSP')
        elif self._dac_resolution == 14:
            self.write(':TRAC1:DWID WPR')
            self.write(':TRAC2:DWID WPR')
        else:
            self.log.error("Unsupported DAC resolution: {}.".format(self._dac_resolution))
        # 2. Define one or multiple segments using the various forms of TRAC:DEF
        # done in load_waveform

        # 3. Fill the segments with values and marker data
        # empty at init
        # 4. Select the segment to be output in arbitrary waveform mode using
        self.write(':TRAC1:SEL 1')
        self.write(':TRAC2:SEL 1')

        # Set the directory:
        self.write(':MMEM:CDIR "{0}"'.format(self._pulsed_file_dir))

        constr = self.get_constraints()

        self.sample_rate = constr.sample_rate.default
        self.set_sample_rate(self.sample_rate)

        # todo: implement choosing AMP
        if self._dac_amp_mode != 'direct':
            raise NotImplementedError("Non direct output '{}' not yet implemented."
                                      .format(self._dac_amp_mode))
        self.write(':OUTP1:ROUT DAC')
        self.write(':OUTP2:ROUT DAC')

        ampl = {'a_ch1': constr.a_ch_amplitude.default, 'a_ch2': constr.a_ch_amplitude.default}
        d_ampl_low = {'d_ch1': constr.d_ch_low.default, 'd_ch2': constr.d_ch_low.default,
                      'd_ch3': constr.d_ch_low.default, 'd_ch4': constr.d_ch_low.default}
        d_ampl_high = {'d_ch1': constr.d_ch_high.default, 'd_ch2': constr.d_ch_high.default,
                       'd_ch3': constr.d_ch_high.default, 'd_ch4': constr.d_ch_high.default}

        self.amplitude_list, self.offset_list = self.set_analog_level(amplitude=ampl)
        self.markers_low, self.markers_high = self.set_digital_level(low=d_ampl_low, high=d_ampl_high)
        self.is_output_enabled = self._is_awg_running()
        self.use_sequencer = self.has_sequence_mode()
        self.active_channel = self.get_active_channels()
        self.interleave = self.get_interleave()
        self.current_loaded_asset = ''
        self.current_status = 0
        self._segment_table = [[],[]]   # [0]: ch1, [1]: ch2. Local, read-only copy of the device segment table
        self._flag_segment_table_req_update = True   # local copy requires update


    def get_constraints(self):
        """
        Retrieve the hardware constrains from the Pulsing device.

        @return constraints object: object with pulser constraints as attributes.

        Provides all the constraints (e.g. sample_rate, amplitude, total_length_bins,
        channel_config, ...) related to the pulse generator hardware to the caller.

            SEE PulserConstraints CLASS IN pulser_interface.py FOR AVAILABLE CONSTRAINTS!!!

        If you are not sure about the meaning, look in other hardware files to get an impression.
        If still additional constraints are needed, then they have to be added to the
        PulserConstraints class.

        Each scalar parameter is an ScalarConstraints object defined in cor.util.interfaces.
        Essentially it contains min/max values as well as min step size, default value and unit of
        the parameter.

        PulserConstraints.activation_config differs, since it contain the channel
        configuration/activation information of the form:
            {<descriptor_str>: <channel_set>,
             <descriptor_str>: <channel_set>,
             ...}

        If the constraints cannot be set in the pulsing hardware (e.g. because it might have no
        sequence mode) just leave it out so that the default is used (only zeros).
        """
        constraints = PulserConstraints()

        # The compatible file formats are hardware specific.
        constraints.waveform_format = ['bin']
        constraints.dac_resolution = {'min': 12, 'max': 14, 'step': 2,
                                      'unit': 'bit'}

        if self._MODEL != 'M8190A':
            self.log.error('This driver is for Keysight M8190A only, but detected: {}'.format(
                self._MODEL
            ))

        if self._dac_resolution == 12:
            constraints.sample_rate.min = 125e6/self._sample_rate_div
            constraints.sample_rate.max = 12e9/self._sample_rate_div
            constraints.sample_rate.step = 1.0e7
            constraints.sample_rate.default = 12e9/self._sample_rate_div
        elif self._dac_resolution == 14:
            constraints.sample_rate.min = 125e6/self._sample_rate_div
            constraints.sample_rate.max = 8e9/self._sample_rate_div
            constraints.sample_rate.step = 1.0e7
            constraints.sample_rate.default = 8e9/self._sample_rate_div
        else:
            raise ValueError("Unsupported DAX resolution: {}".format(self._dac_resolution))

        # manual 8.22.3 Waveform Granularity and Size
        if self._dac_resolution == 12:
            constraints.waveform_length.step = 64
            constraints.waveform_length.min = 320
            constraints.waveform_length.default = 320
        elif self._dac_resolution == 14:
            constraints.waveform_length.step = 48
            constraints.waveform_length.min = 240
            constraints.waveform_length.default = 240

        constraints.a_ch_amplitude.min = 0.100     # Channels amplitude control single ended min
        constraints.a_ch_amplitude.max = 0.700      # Channels amplitude control single ended max
        if self._dac_resolution == 12:
            constraints.a_ch_amplitude.step = 1.7090e-4  # for AWG8190: actually 0.7Vpp/2^12=0.0019; for DAC resolution of 12 bits (data sheet p. 17)
        elif self._dac_resolution == 14:
            constraints.a_ch_amplitude.step = 4.2725e-5
        constraints.a_ch_amplitude.default = 0.500

        constraints.d_ch_low.min = -0.5
        constraints.d_ch_low.max = 1.75
        constraints.d_ch_low.step = 0.0002
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = -0.5
        constraints.d_ch_high.max = 1.75
        constraints.d_ch_high.step = 0.0002
        constraints.d_ch_high.default = 1.5

        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 16_000_000
        constraints.waveform_num.default = 1
        # The sample memory can be split into a maximum of 16 M waveform segments

        # FIXME: Check the proper number for your device
        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 4000
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1

        constraints.sequence_option = SequenceOption.OPTIONAL
        constraints.sequence_order = SequenceOrderOption.LINONLY

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65536
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0

        # ToDo: Check how many external triggers are available
        # constraints.trigger_in.min = 0
        # constraints.trigger_in.max = 1
        # constraints.trigger_in.step = 1
        # constraints.trigger_in.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names
        # for the different configurations can be customary chosen.

        activation_config = OrderedDict()

        if self._MODEL == 'M8190A':
            # all allowed configs
            # digital channels belong to analogue counterparts
            activation_config['all'] = {'a_ch1', 'a_ch2',
                                        'd_ch1', 'd_ch2', 'd_ch3', 'd_ch4'}
            # sample marker are more accurate than sync markers -> lower d_ch numbers
            activation_config['ch1_2mrk'] = {'a_ch1',
                                            'd_ch1', 'd_ch3'}
            activation_config['ch2_2mrk'] = {'a_ch2',
                                             'd_ch2', 'd_ch4'}



        constraints.activation_config = activation_config

        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        self.write(':OUTP1:NORM ON')
        self.write(':OUTP2:NORM ON')

        # Sec. 6.4 from manual:
        # In the program it is recommended to send the command for starting
        # data generation (:INIT:IMM) as the last command. This way
        # intermediate stop/restarts (e.g. when changing sample rate or
        # loading a waveform) are avoided and optimum execution performance is
        # achieved.

        # wait until the AWG switched the outputs on
        while not self._is_output_on():
            time.sleep(0.25)

        self.write(':INIT:IMM')
        self.write('*WAI')

        # in dynamic mode with external pattern jump, we start by a software trigger
        # subsequent triggers are generated by external control hw
        if self.get_trigger_mode() == "trig" and self.get_dynamic_mode():
            self.send_trigger_event()

        self.current_status = 1
        self.is_output_enabled = True
        return self.current_status

    def pulser_off(self):
        """ Switches the pulsing device off.
        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self.write(':ABOR')

        # wait until the AWG has actually stopped
        while self._is_awg_running():
            time.sleep(0.25)

        self.current_status = 0
        self.is_output_enabled = False
        return self.current_status

    def load_waveform(self, load_dict, to_nextfree_segment=False):
        """ Loads a waveform to the specified channel of the pulsing device.

        @param dict|list load_dict: a dictionary with keys being one of the available channel
                                    index and values being the name of the already written
                                    waveform to load into the channel.
                                    Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                {1: rabi_ch2, 2: rabi_ch1}
                                    If just a list of waveform names is given, the channel
                                    association will be invoked from the channel
                                    suffix '_ch1', '_ch2' etc.

                                        {1: rabi_ch1, 2: rabi_ch2}
                                    or
                                        {1: rabi_ch2, 2: rabi_ch1}

                                    If just a list of waveform names is given,
                                    the channel association will be invoked from
                                    the channel suffix '_ch1', '_ch2' etc. A
                                    possible configuration can be e.g.

                                        ['rabi_ch1', 'rabi_ch2', 'rabi_ch3']

        @return dict: Dictionary containing the actually loaded waveforms per
                      channel.

        For devices that have a workspace (i.e. AWG) this will load the waveform
        from the device workspace into the channel. For a device without mass
        memory, this will make the waveform/pattern that has been previously
        written with self.write_waveform ready to play.

        Please note that the channel index used here is not to be confused with the number suffix
        in the generic channel descriptors (i.e. 'd_ch1', 'a_ch1'). The channel index used here is
        highly hardware specific and corresponds to a collection of digital and analog channels
        being associated to a SINGLE wavfeorm asset.
        """

        if isinstance(load_dict, list):
            new_dict = dict()
            for waveform in load_dict:
                channel = int(waveform.rsplit('_ch', 1)[1][0])
                new_dict[channel] = waveform
            load_dict = new_dict

        # Get all active channels
        chnl_activation = self.get_active_channels()
        analog_channels = sorted(
            chnl for chnl in chnl_activation if chnl.startswith('a') and chnl_activation[chnl])

        # Check if all channels to load to are active
        channels_to_set = {'a_ch{0:d}'.format(chnl_num) for chnl_num in load_dict}
        if not channels_to_set.issubset(analog_channels):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more channels to set are not active.\n'
                           'channels_to_set are: ', channels_to_set, 'and\n'
                           'analog_channels are: ', analog_channels)
            return self.get_loaded_assets()

        # Check if all waveforms to load are present on device memory
        if not set(load_dict.values()).issubset(self.get_waveform_names()):
            self.log.error('Unable to load waveforms into channels.\n'
                           'One or more waveforms to load are missing on pc memory: {}'.format(
                                                                            set(load_dict.values())
            ))
            return self.get_loaded_assets()

        if load_dict == {}:
            self.log.warning('No file and channel provided for load!\n'
                             'Correct that!\nCommand will be ignored.')
            return self.get_loaded_assets()

        if not to_nextfree_segment:
            self.clear_all()
        path = self._pulsed_file_dir
        offset = 0

        for chnl_num, waveform in load_dict.items():
            name = waveform.split('.bin', 1)[0]
            filepath = os.path.join(path, waveform)
            # todo: potentially faster to write data from PC ram without storing to hdd first
            data = self.query_bin(':MMEM:DATA? "{0}"'.format(filepath))
            samples = len(data)
            segment_id = self.query('TRAC{0:d}:DEF:NEW? {1:d}'.format(chnl_num, samples)) \
                        + '_ch{:d}'.format(chnl_num)
            segment_id_per_ch = segment_id.rsplit("_ch",1)[0]
            self.write_bin(':TRAC{0}:DATA {1}, {2},'.format(chnl_num, segment_id_per_ch, offset), data)
            self.write(':TRAC{0}:NAME {1}, "{2}"'.format(chnl_num, segment_id_per_ch, name))

            self._flag_segment_table_req_update = True
            self.log.debug("Loading waveform {} of len {} to AWG ch {}, segment {}.".format(
                name, samples, chnl_num, segment_id_per_ch))

        self.set_trigger_mode('cont')

        return self.get_loaded_assets()

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param dict|list sequence_name: a dictionary with keys being one of the available channel
                                        index and values being the name of the already written
                                        waveform to load into the channel.
                                        Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                    {1: rabi_ch2, 2: rabi_ch1}
                                        If just a list of waveform names if given, the channel
                                        association will be invoked from the channel
                                        suffix '_ch1', '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """


        # Get all active channels
        chnl_activation = self.get_active_channels()
        analog_channels = sorted(
            chnl for chnl in chnl_activation if chnl.startswith('a') and chnl_activation[chnl])

        # Number of channels that have this sequence set
        n_ready_ch = len(self.get_loaded_assets())
        if n_ready_ch != len(analog_channels):
            self.log.error('Unable to load sequence.\nNumber of tracks in sequence to load does '
                           'not match the number of active analog channels.')
            return self.get_loaded_assets()

        if not (set(self.get_loaded_assets()[0].values())).issubset(set([sequence_name])):
            self.log.error('Unable to load sequence into channels.\n'
                           'Make sure to call write_sequence() first.')
            return self.get_loaded_assets()

        """
        select the first segment in your sequence, before any dynamic sequence selection.
        """
        self.write(":STAB1:SEQ:SEL 0")
        self.write(":STAB2:SEQ:SEL 0")
        self.write(":STAB1:DYN ON")
        self.write(":STAB2:DYN ON")

        return 0

    def send_trigger_event(self):
        self.write(":TRIG:BEG")

    def set_trigger_mode(self, mode="cont"):
        """
        Trigger mode according to manual 3.3.
        :param mode: "cont", "trig" or "gate"
        :return:
        """
        if mode is "cont":
            self.write(":INIT:CONT1:STAT ON")
            self.write(":INIT:GATE1:STAT OFF")
            self.write(":INIT:CONT2:STAT ON")
            self.write(":INIT:GATE2:STAT OFF")
        elif mode is "trig":
            self.write(":INIT:CONT1:STAT OFF")
            self.write(":INIT:GATE1:STAT OFF")
            self.write(":INIT:CONT2:STAT OFF")
            self.write(":INIT:GATE2:STAT OFF")
        elif mode is "gate":
            self.write(":INIT:CONT1:STAT OFF")
            self.write(":INIT:GATE1:STAT ON")
            self.write(":INIT:CONT2:STAT OFF")
            self.write(":INIT:GATE2:STAT ON")
        else:
            self.log.error("Unknown trigger mode: {}".format(mode))

    def get_trigger_mode(self):
        cont_ch1 = bool(int(self.query(":INIT:CONT1:STAT?")))
        cont_ch2 = bool(int(self.query(":INIT:CONT1:STAT?")))
        gate_ch1 = bool(int(self.query(":INIT:GATE1:STAT?")))
        gate_ch2 = bool(int(self.query(":INIT:GATE2:STAT?")))

        if cont_ch1 and cont_ch2 and not gate_ch1 and not gate_ch2:
            return "cont"
        if not cont_ch1 and not cont_ch1 and not gate_ch1 and not gate_ch2:
            return "trig"
        if not cont_ch1 and not cont_ch2 and gate_ch1 and gate_ch2:
            return "gate"

        self.log.warning("Unexpected trigger mode found. Cont (ch1/ch2): {}/{}, Gate {}/{}".format(
                            cont_ch1, cont_ch2, gate_ch1, gate_ch2))
        return ""

    def get_dynamic_mode(self):
        retval = self.query(":STAB1:DYN?") and self.query(":STAB2:DYN?")
        return retval

    def check_dev_error(self):

        has_error_occured = False

        for i in range(30):  # error buffer of device is 30
            raw_str = self.query(':SYST:ERR?', force_no_check=True)
            is_error = not ('0' in raw_str[0])
            if is_error:
                self.log.warn("AWG issued error: {}".format(raw_str))
                has_error_occured = True
            else:
                break

        return has_error_occured

    def get_loaded_assets(self):
        """
        Retrieve the currently loaded asset names for each active channel of the device.
        The returned dictionary will have the channel numbers as keys.
        In case of loaded waveforms the dictionary values will be the waveform names.
        In case of a loaded sequence the values will be the sequence name appended by a suffix
        representing the track loaded to the respective channel (i.e. '<sequence_name>_1').

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel,
                             string describing the asset type ('waveform' or 'sequence')
        """

        # Get all active channels
        chnl_activation = self.get_active_channels()
        channel_numbers = sorted(int(chnl.split('_ch')[1]) for chnl in chnl_activation if
                                 chnl.startswith('a') and chnl_activation[chnl])

        # Get assets per channel
        loaded_assets = dict()
        type_per_ch = []
        is_err = False

        for chnl_num in channel_numbers:

            asset_name = 'ERROR_NAME'

            if self.get_loaded_assets_num(chnl_num, mode='segment') == 1 \
                and self.get_loaded_assets_num(chnl_num, mode='sequence') == 0:

                type_per_ch.append('waveform')
                asset_name = self.get_loaded_assets_name(chnl_num, mode='segment')[0]

            elif self.get_loaded_assets_num(chnl_num, mode='segment') >= 1 \
                and self.get_loaded_assets_num(chnl_num, mode='sequence') == 1:

                type_per_ch.append('sequence')
                asset_name = self.get_loaded_assets_name(chnl_num, mode='sequence')[0]
            elif self.get_loaded_assets_num(chnl_num, mode='segment') == 0 \
                and self.get_loaded_assets_num(chnl_num, mode='sequence') == 0:

                type_per_ch.append('waveform')
                asset_name = ''

            else:
                is_err = True

            if self.get_loaded_assets_num(chnl_num, mode='segment') > 1 \
                and self.get_loaded_assets_num(chnl_num, mode='sequence') == 0:

                self.log.error("Multiple segments, but no sequence defined")

            if self.get_loaded_assets_num(chnl_num, mode='sequence') > 1:
                self.log.error("Multiple sequences defined. Should only be 1.")
                # todo: implement more than 1 sequence

            loaded_assets[chnl_num] = asset_name

        if not all(x == type_per_ch[0] for x in type_per_ch):
            is_err = True
        if is_err:
            self.log.error('Unable to determine loaded assets.')
            return dict(), ''

        return loaded_assets, type_per_ch[0]

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without storage capability
        (PulseBlaster, FPGA).
        """

        self.write(':TRAC1:DEL:ALL')
        self.write(':TRAC2:DEL:ALL')
        self._flag_segment_table_req_update = True
        self.current_loaded_asset = ''

        return

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): inter value of the current status with the
                             corresponding dictionary containing status
                             description for all the possible status variables
                             of the pulse generator hardware
        """

        status_dic = {-1: 'Failed Request or Communication',
                       0: 'Device has stopped, but can receive commands',
                       1: 'Device is active and running'}

        current_status = -1 if self.awg is None else int(self._is_awg_running())
        # All the other status messages should have higher integer values then 1.

        return current_status, status_dic

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead retrieve the current
        sample rate directly from the device.
        """
        self.sample_rate = float(self.query(':FREQ:RAST?')) / self._sample_rate_div
        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """
        sample_rate_GHz = (sample_rate * self._sample_rate_div) / 1e9
        self.write(':FREQ:RAST {0:.4G}GHz\n'.format(sample_rate_GHz))
        while int(self.query('*OPC?')) != 1:
            time.sleep(0.25)
        time.sleep(0.2)
        return self.get_sample_rate()

    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if the amplitude value (in Volt peak to peak, i.e. the
                               full amplitude) of a specific channel is desired.
        @param list offset: optional, if the offset value (in Volt) of a specific channel is
                            desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor string
                               (i.e. 'a_ch1') and items being the values for those channels.
                               Amplitude is always denoted in Volt-peak-to-peak and Offset in volts.

        Note: Do not return a saved amplitude and/or offset value but instead retrieve the current
              amplitude and/or offset directly from the device.

        If nothing (or None) is passed then the levels of all channels will be returned. If no
        analog channels are present in the device, return just empty dicts.

        Example of a possible input:
            amplitude = ['a_ch1', 'a_ch4'], offset = None
        to obtain the amplitude of channel 1 and 4 and the offset of all channels
            {'a_ch1': -0.5, 'a_ch4': 2.0} {'a_ch1': 0.0, 'a_ch2': 0.0, 'a_ch3': 1.0, 'a_ch4': 0.0}
        """

        amp = dict()
        off = dict()

        chnl_list = self._get_all_analog_channels()

        # get pp amplitudes
        if amplitude is None:
            for ch_num, chnl in enumerate(chnl_list, 1):
                amp[chnl] = float(self.query(':VOLT{0:d}?'.format(ch_num)))
        else:
            for chnl in amplitude:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    amp[chnl] = float(self.query(':VOLT{0:d}?'.format(ch_num)))
                else:
                    self.log.warning('Get analog amplitude from M8195A channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))

        # get voltage offsets
        if offset is None:
            for ch_num, chnl in enumerate(chnl_list):
                off[chnl] = 0.0
        else:
            for chnl in offset:
                if chnl in chnl_list:
                    ch_num = int(chnl.rsplit('_ch', 1)[1])
                    off[chnl] = float(self.query(':VOLT{0:d}:OFFS?'.format(ch_num)))
                else:
                    self.log.warning('Get analog offset from M8195A channel "{0}" failed. '
                                     'Channel non-existent.'.format(chnl))
        return amp, off

    def set_analog_level(self, amplitude=None, offset=None):
        """ Set amplitude and/or offset value of the provided analog channel(s).

        @param dict amplitude: dictionary, with key being the channel descriptor string
                               (i.e. 'a_ch1', 'a_ch2') and items being the amplitude values
                               (in Volt peak to peak, i.e. the full amplitude) for the desired
                               channel.
        @param dict offset: dictionary, with key being the channel descriptor string
                            (i.e. 'a_ch1', 'a_ch2') and items being the offset values
                            (in absolute volt) for the desired channel.

        @return (dict, dict): tuple of two dicts with the actual set values for amplitude and
                              offset for ALL channels.

        If nothing is passed then the command will return the current amplitudes/offsets.

        Note: After setting the amplitude and/or offset values of the device, use the actual set
              return values for further processing.
        """
        # Check the inputs by using the constraints...
        constraints = self.get_constraints()
        # ...and the available analog channels
        analog_channels = self._get_all_analog_channels()

        # amplitude sanity check
        if amplitude is not None:
            for chnl in amplitude:
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                if chnl not in analog_channels:
                    self.log.warning('Channel to set (a_ch{0}) not available in AWG.\nSetting '
                                     'analogue voltage for this channel ignored.'.format(ch_num))
                    del amplitude[chnl]
                if amplitude[chnl] < constraints.a_ch_amplitude.min:
                    self.log.warning('Minimum Vpp for channel "{0}" is {1}. Requested Vpp of {2}V '
                                     'was ignored and instead set to min value.'
                                     ''.format(chnl, constraints.a_ch_amplitude.min,
                                               amplitude[chnl]))
                    amplitude[chnl] = constraints.a_ch_amplitude.min
                elif amplitude[chnl] > constraints.a_ch_amplitude.max:
                    self.log.warning('Maximum Vpp for channel "{0}" is {1}. Requested Vpp of {2}V '
                                     'was ignored and instead set to max value.'
                                     ''.format(chnl, constraints.a_ch_amplitude.max,
                                               amplitude[chnl]))
                    amplitude[chnl] = constraints.a_ch_amplitude.max
        # offset sanity check
        if offset is not None:
            for chnl in offset:
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                if chnl not in analog_channels:
                    self.log.warning('Channel to set (a_ch{0}) not available in AWG.\nSetting '
                                     'offset voltage for this channel ignored.'.format(chnl))
                    del offset[chnl]
                if offset[chnl] < constraints.a_ch_offset.min:
                    self.log.warning('Minimum offset for channel "{0}" is {1}. Requested offset of '
                                     '{2}V was ignored and instead set to min value.'
                                     ''.format(chnl, constraints.a_ch_offset.min, offset[chnl]))
                    offset[chnl] = constraints.a_ch_offset.min
                elif offset[chnl] > constraints.a_ch_offset.max:
                    self.log.warning('Maximum offset for channel "{0}" is {1}. Requested offset of '
                                     '{2}V was ignored and instead set to max value.'
                                     ''.format(chnl, constraints.a_ch_offset.max,
                                               offset[chnl]))
                    offset[chnl] = constraints.a_ch_offset.max

        if amplitude is not None:
            for chnl, amp in amplitude.items():
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                self.write(':VOLT{0} {1:.4f}'.format(ch_num, amp))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.25)

        if offset is not None:
            for chnl, off in offset.items():
                ch_num = int(chnl.rsplit('_ch', 1)[1])
                self.write(':VOLT{0}:OFFS {1:.4f}'.format(ch_num, off))
                while int(self.query('*OPC?')) != 1:
                    time.sleep(0.25)
        return self.get_analog_level()


    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels.

        @param list low: optional, if the low value (in Volt) of a specific channel is desired.
        @param list high: optional, if the high value (in Volt) of a specific channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor strings
                               (i.e. 'd_ch1', 'd_ch2') and items being the values for those
                               channels. Both low and high value of a channel is denoted in volts.

        Note: Do not return a saved low and/or high value but instead retrieve
              the current low and/or high value directly from the device.

        If nothing (or None) is passed then the levels of all channels are being returned.
        If no digital channels are present, return just an empty dict.

        Example of a possible input:
            low = ['d_ch1', 'd_ch4']
        to obtain the low voltage values of digital channel 1 an 4. A possible answer might be
            {'d_ch1': -0.5, 'd_ch4': 2.0} {'d_ch1': 1.0, 'd_ch2': 1.0, 'd_ch3': 1.0, 'd_ch4': 4.0}
        Since no high request was performed, the high values for ALL channels are returned (here 4).
        """

        low_val = {}
        high_val = {}

        digital_channels = self._get_all_digital_channels()

        if low is None:
            low = digital_channels
        if high is None:
            high = digital_channels

        # get low marker levels
        for chnl in low:
            if chnl not in digital_channels:
                continue
            d_ch_int = self._digital_ch_2_internal(chnl)
            low_val[chnl] = float(
                self.query(':{}:VOLT:LOW?'.format(d_ch_int)))
        # get high marker levels
        for chnl in high:
            if chnl not in digital_channels:
                continue
            d_ch_int = self._digital_ch_2_internal(chnl)
            high_val[chnl] = float(
                self.query(':{}:VOLT:HIGH?'.format(d_ch_int)))

        return low_val, high_val

    def _digital_ch_2_internal(self, d_ch_name):
        if d_ch_name not in self.ch_map:
            self.log.error("Don't understand digital channel name: {}".format(d_ch_name))

        return self.ch_map[str(d_ch_name)]

    def _digital_ch_corresponding_analogue_ch(self, d_ch_name):
        int_name = self._digital_ch_2_internal(d_ch_name)
        if '1' in int_name:
            return 'a_ch1'
        elif '2' in int_name:
            return  'a_ch2'
        else:
            raise RuntimeError("Unknown exception. Should only have 1 or 2 in marker name")

    def _analogue_ch_corresponding_digital_chs(self, a_ch_name):
        # return value must be: [sample marker, sync marker]
        return self.ch_map_a2d[a_ch_name]

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel.

        @param dict low: dictionary, with key being the channel descriptor string
                         (i.e. 'd_ch1', 'd_ch2') and items being the low values (in volt) for the
                         desired channel.
        @param dict high: dictionary, with key being the channel descriptor string
                          (i.e. 'd_ch1', 'd_ch2') and items being the high values (in volt) for the
                          desired channel.

        @return (dict, dict): tuple of two dicts where first dict denotes the current low value and
                              the second dict the high value for ALL digital channels.
                              Keys are the channel descriptor strings (i.e. 'd_ch1', 'd_ch2')

        If nothing is passed then the command will return the current voltage levels.

        Note: After setting the high and/or low values of the device, use the actual set return
              values for further processing.
        """
        if low is None:
            low = self.get_digital_level()[0]
        if high is None:
            high = self.get_digital_level()[1]

        #If you want to check the input use the constraints:
        constraints = self.get_constraints()
        digital_channels = self._get_all_digital_channels()

        # Check the constraints for marker high level
        for key in high:
            if high[key] < constraints.d_ch_high.min:
                self.log.warning('Voltages for digital values are too small for high. Setting to minimum value')
                high[key] = constraints.d_ch_high.min
            elif high[key] > constraints.d_ch_high.max:
                self.log.warning('Voltages for digital values are too high for high. Setting to maximum value')
                high[key] = constraints.d_ch_high.max

        # Check the constraints for marker low level
        for key in low:
            if low[key] < constraints.d_ch_low.min:
                self.log.warning('Voltages for digital values are too small for low. Setting to minimum value')
                low[key] = constraints.d_ch_low.min
            elif low[key] > constraints.d_ch_low.max:
                self.log.warning('Voltages for digital values are too high for low. Setting to maximum value')
                low[key] = constraints.d_ch_low.max

        # Check the difference between marker high and low
        for key in high:
            if high[key] - low[key] < 0.125:
                self.log.warning('Voltage difference is too small. Reducing low voltage level.')
                low[key] = high[key] - 0.125
            elif high[key] - low[key] > 2.25:
                self.log.warning('Voltage difference is too large. Increasing low voltage level.')
                low[key] = high[key] - 2.25


        # set high marker levels
        for chnl in low and high:
            if chnl not in digital_channels:
                continue
            d_ch_internal = self._digital_ch_2_internal(chnl)
            offs =(high[chnl] + low[chnl])/2
            ampl = high[chnl] - low[chnl]
            self.write('{0}:VOLT:AMPL {1}'.format(d_ch_internal, ampl))
            self.write('{0}:VOLT:OFFS {1}'.format(d_ch_internal, offs))

        return self.get_digital_level()


    def get_active_channels(self, ch=None, set_ac=True):
        """ Get the active channels of the pulse generator hardware.

        @param list ch: optional, if specific analog or digital channels are needed to be asked
                        without obtaining all the channels.

        @return dict:  where keys denoting the channel string and items boolean expressions whether
                       channel are active or not.

        Example for an possible input (order is not important):
            ch = ['a_ch2', 'd_ch2', 'a_ch1', 'd_ch5', 'd_ch1']
        then the output might look like
            {'a_ch2': True, 'd_ch2': False, 'a_ch1': False, 'd_ch5': True, 'd_ch1': False}

        If no parameter (or None) is passed to this method all channel states will be returned.
        """
        # analog_channels = self._get_all_analog_channels()
        #
        # active_ch = dict()
        # for ch_num, a_ch in enumerate(analog_channels, 1):
        #     # check what analog channels are active
        #     active_ch[a_ch] = bool(int(self.query(':OUTP{0}?'.format(ch_num))))
        #
        # # return either all channel information or just the one asked for.
        # if ch is not None:
        #     chnl_to_delete = [chnl for chnl in active_ch if chnl not in ch]
        #     for chnl in chnl_to_delete:
        #         del active_ch[chnl]

        if ch is None:
            ch = []

        active_ch = dict()

        if ch ==[]:
            active_ch['a_ch1'] = bool(int(self.query(':OUTP1:NORM?')))
            active_ch['a_ch2'] = bool(int(self.query(':OUTP2:NORM?')))

            # marker channels are active if corresponding analogue channel on
            active_ch['d_ch1'] = active_ch[self._digital_ch_corresponding_analogue_ch('d_ch1')]
            active_ch['d_ch2'] = active_ch[self._digital_ch_corresponding_analogue_ch('d_ch2')]
            active_ch['d_ch3'] = active_ch[self._digital_ch_corresponding_analogue_ch('d_ch3')]
            active_ch['d_ch4'] = active_ch[self._digital_ch_corresponding_analogue_ch('d_ch4')]

        else:
            for channel in ch:
                if 'a_ch' in channel:
                    ana_chan = int(channel[4:])
                    active_ch[channel] = bool(int(self.ask(':OUTP{0}:NORM?'.format(ana_chan))))

                elif 'd_ch'in channel:
                    active_ch[channel] = active_ch[self._digital_ch_corresponding_analogue_ch(channel)]

        if set_ac:
            self.active_channel = active_ch

        return active_ch


    def set_active_channels(self, ch=None):
        """
        Set the active/inactive channels for the pulse generator hardware.
        The state of ALL available analog and digital channels will be returned
        (True: active, False: inactive).
        The actually set and returned channel activation must be part of the available
        activation_configs in the constraints.
        You can also activate/deactivate subsets of available channels but the resulting
        activation_config must still be valid according to the constraints.
        If the resulting set of active channels can not be found in the available
        activation_configs, the channel states must remain unchanged.

        @param dict ch: dictionary with keys being the analog or digital string generic names for
                        the channels (i.e. 'd_ch1', 'a_ch2') with items being a boolean value.
                        True: Activate channel, False: Deactivate channel

        @return dict: with the actual set values for ALL active analog and digital channels

        If nothing is passed then the command will simply return the unchanged current state.

        Note: After setting the active channels of the device, use the returned dict for further
              processing.

        Example for possible input:
            ch={'a_ch2': True, 'd_ch1': False, 'd_ch3': True, 'd_ch4': True}
        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1. All other available channels will remain unchanged.
        """
        current_channel_state = self.get_active_channels()

        if ch is None:
            return current_channel_state

        if not set(current_channel_state).issuperset(ch):
            self.log.error('Trying to (de)activate channels that are not present in M8190A.\n'
                           'Setting of channel activation aborted.')
            return current_channel_state

        # Determine new channel activation states
        new_channels_state = current_channel_state.copy()
        for chnl in ch:
            new_channels_state[chnl] = ch[chnl]

        # iterate digital channels and activate if corresponding analogue is on
        for chnl in current_channel_state.copy():
            if chnl.startswith('d_'):
                if new_channels_state[self._digital_ch_corresponding_analogue_ch(chnl)]:
                    new_channels_state[chnl] = True
                else:
                    new_channels_state[chnl] = False

        # check if the channels to set are part of the activation_config constraints
        constraints = self.get_constraints()
        new_active_channels = {chnl for chnl in new_channels_state if new_channels_state[chnl]}
        if new_active_channels not in constraints.activation_config.values():
            self.log.error('activation_config to set ({0}) is not allowed according to constraints.'
                           ''.format(new_active_channels))
            return current_channel_state

        # get lists of all analog channels
        analog_channels = self._get_all_analog_channels()
        digital_channels = self._get_all_digital_channels()

        # Also (de)activate the channels accordingly
        for a_ch in analog_channels:
            ach_num = int(a_ch.rsplit('_ch', 1)[1])
            # (de)activate the analog channel
            if new_channels_state[a_ch]:
                self.write('OUTP{0:d}:NORM ON'.format(ach_num))
            else:
                self.write('OUTP{0:d}:NORM OFF'.format(ach_num))

        # digital channels belong to analogue ones

        return self.get_active_channels(set_ac=True)

    def float_to_sample(self, val):
        """
        :param val: np.array(dtype=float64) of sampled values from sequencegenerator.sample_pulse_block_ensemble().
                    normed (-1...1) where 1 encodes the full Vpp as set in 'PulsedGui/Pulsegenerator Settings'.
                    If MW ampl in 'PulsedGui/Predefined methods' < as full Vpp, amplitude reduction will be
                    performed digitally (reducing the effective digital resolution in bits).
        :return:    np.array(dtype=int16)
        """


        bitsize = int(2**self._dac_resolution)
        shiftbits = 16-self._dac_resolution   # 2 for marker, dac: 12 -> 2, dac: 14 -> 4
        min_intval = -bitsize/2
        max_intval =  bitsize/2 -1

        max_u_samples = 1     # data should be normalized in (-1..1)

        if max(abs(val)) > 1:
            self.log.warning("Samples from sequencegenerator out of range. Normalizing to -1..1")
            biggest_val = max([abs(np.min(val)), np.max(val)])
            max_u_samples = biggest_val
        # manual 8.22.4 Waveform Data Format in Direct Mode
        # 2 bits LSB reserved for markers
        mapper = scipy.interpolate.interp1d([-max_u_samples,max_u_samples],[min_intval, max_intval])
        return mapper(val).astype('int16') << shiftbits

    def bool_to_sample(self, marker_val_sample, marker_val_sync):
        bit_marker = 0x1 & np.asarray(marker_val_sample).astype('int16')
        bit_sync =   0x2 & np.asarray(marker_val_sync).astype('int16') << 1

        return bit_marker + bit_sync

    def write_waveform(self, name, analog_samples, digital_samples, is_first_chunk, is_last_chunk,
                       total_number_of_samples):
        """
        Write a new waveform or append samples to an already existing waveform.
        Keysight AWG doesn't have own mass memory, so waveforms are sampled to local computer dir.
        The flags is_first_chunk and is_last_chunk can be used as indicator if a new waveform should
        be created or if the write process to a waveform should be terminated.

        NOTE: All sample arrays in analog_samples and digital_samples must be of equal length!

        @param str name: the name of the waveform to be created/append to
        @param dict analog_samples: keys are the generic analog channel names (i.e. 'a_ch1') and
                                    values are 1D numpy arrays of type float32 containing the
                                    voltage samples.
        @param dict digital_samples: keys are the generic digital channel names (i.e. 'd_ch1') and
                                     values are 1D numpy arrays of type bool containing the marker
                                     states.
        @param bool is_first_chunk: Flag indicating if it is the first chunk to write.
                                    If True this method will create a new empty wavveform.
                                    If False the samples are appended to the existing waveform.
        @param bool is_last_chunk:  Flag indicating if it is the last chunk to write.
                                    Some devices may need to know when to close the appending wfm.
        @param int total_number_of_samples: The number of sample points for the entire waveform
                                            (not only the currently written chunk)

        @return (int, list): Number of samples written (-1 indicates failed process) and list of
                             created waveform names
        """

        waveforms = list()

        # Sanity checks
        if len(analog_samples) == 0:
            self.log.error('No analog samples passed to write_waveform method in M8190A.')
            return -1, waveforms

        min_samples = self.get_constraints().waveform_length.min
        if total_number_of_samples < min_samples:
            self.log.error('Unable to write waveform.\nNumber of samples to write ({0:d}) is '
                           'smaller than the allowed minimum waveform length ({1:d}).'
                           ''.format(total_number_of_samples, min_samples))
            return -1, waveforms

        # determine active channels
        activation_dict = self.get_active_channels()
        active_channels = {chnl for chnl in activation_dict if activation_dict[chnl]}
        active_analog = sorted(chnl for chnl in active_channels if chnl.startswith('a'))

        # Sanity check of channel numbers
        if active_channels != set(analog_samples.keys()).union(set(digital_samples.keys())):
            self.log.error('Mismatch of channel activation and sample array dimensions for '
                           'waveform creation.\nChannel activation is: {0}\nSample arrays have: '
                           ''.format(active_channels,
                                     set(analog_samples.keys()).union(set(digital_samples.keys()))))
            return -1, waveforms

        self.write(':FUNC1:MODE ARB')  # set to arbitrary mode
        self.write(':FUNC2:MODE ARB')

        marker = True   # no reason to deactivate any marker for M8190A, as active makers do not impose restrcitions

        for channel_index, channel_number in enumerate(active_analog):

            self.log.debug('Max ampl, ch={0}: {1}'.format(channel_number, analog_samples[channel_number].max()))

            a_samples = self.float_to_sample(analog_samples[channel_number])
            marker_sample = digital_samples[self._analogue_ch_corresponding_digital_chs(channel_number)[0]]
            marker_sync = digital_samples[self._analogue_ch_corresponding_digital_chs(channel_number)[1]]
            d_samples = self.bool_to_sample(marker_sample, marker_sync)
            if marker:
                comb_samples = a_samples + d_samples
            else:
                comb_samples = a_samples
            filename = name + '_ch' + str(channel_index + 1) + '.bin'  # all names lowercase to avoid trouble
            waveforms.append(filename)

            if channel_index == 0:
                # deletes waveform, all channels
                self.delete_waveform(filename.split("_ch")[0])
            self.write_bin(':MMEM:DATA "{0}", '.format(filename), comb_samples)
            self.log.debug("Waveform {} written to {}".format(name, filename))

        self.check_dev_error()

        return total_number_of_samples, waveforms

    def write_sequence(self, name, sequence_parameters):
        """
        Write a new sequence on the device memory.
        If elements in the sequence are not available on the AWG yet, they will be
        transfered from the PC.

        @param str name: the name of the waveform to be created/append to
        @param dict sequence_parameters: dictionary containing the parameters for a sequence

        @return: int, number of sequence steps written (-1 indicates failed process)
        """

        # Check if device has sequencer option installed
        if not self.has_sequence_mode():
            self.log.error('Direct sequence generation in AWG not possible. Sequencer option not '
                           'installed.')
            return -1

        # Check if all waveforms are present on device memory
        avail_waveforms = set(self.get_waveform_names())
        for waveform_tuple, param_dict in sequence_parameters:
            if not avail_waveforms.issuperset(waveform_tuple):
                self.log.error('Failed to create sequence "{0}" due to waveforms "{1}" not '
                               'present in pc memory.'.format(name, waveform_tuple))
                return -1

        # todo: check sequence mathces num_tracks

        active_analog = natural_sort(chnl for chnl in self.get_active_channels() if chnl.startswith('a'))
        num_tracks = len(active_analog)
        num_steps = len(sequence_parameters)

        # define new sequence
        self.write(':FUNC1:MODE STS')  # activate the sequence mode
        self.write(':FUNC2:MODE STS')
        self.write(':STAB1:RES')  # Reset all sequence table entries to default values
        self.write(':STAB2:RES')
        self.write(':SEQ1:DEL:ALL')
        self.write(':SEQ2:DEL:ALL')
        self.write(':ARM:DYNP:WIDT LOW')  # Only use lower 13 bits of dynamic input

        seq_id_ch1 = int(self.query(":SEQ1:DEF:NEW? {:d}".format(num_steps)))
        seq_id_ch2 = int(self.query(":SEQ2:DEF:NEW? {:d}".format(num_steps)))
        if seq_id_ch1 != seq_id_ch2:
            self.log.warning("Sequence tables for channels seem not aligned.")
        self.write(":SEQ1:NAME {:d}, '{}'".format(seq_id_ch1, name))
        self.write(":SEQ2:NAME {:d}, '{}'".format(seq_id_ch2, name))

        loaded_segments_ch1 = self.get_loaded_assets_name(1, mode='segment')
        loaded_segments_ch2 = self.get_loaded_assets_name(2, mode='segment')

        waves_loaded_here = []
        # transfer waveforms in sequence from local pc to segments in awg mem
        for waveform_tuple, param_dict in sequence_parameters:
            # todo: handle other than 2 channels
            waveform_list = []
            waveform_list.append(waveform_tuple[0])
            waveform_list.append(waveform_tuple[1])
            wave_ch1 = self._remove_file_extension(waveform_tuple[0])
            wave_ch2 = self._remove_file_extension(waveform_tuple[1])

            if not (wave_ch1 in loaded_segments_ch1 and
                    wave_ch2 in loaded_segments_ch2) \
                    and not (wave_ch1 in waves_loaded_here and
                    wave_ch2 in waves_loaded_here):

                self.log.debug("Couldn't find segments {} and {} on device for writing sequence {}. Loading...".format(
                    wave_ch1, wave_ch2, name))
                self.load_waveform(waveform_list, to_nextfree_segment=True)
                waves_loaded_here.append(wave_ch1)
                waves_loaded_here.append(wave_ch2)
            else:
                self.log.debug("Segments {} and {} already on device for writing sequence {}. Skipping load.".format(
                    wave_ch1, wave_ch2, name))

        self.log.debug("Loading of waveforms for sequence write finished.")
        """
        Manual: When using dynamic sequencing, the arm mode must be set to self-armed 
        and all advancement modes must be set to Auto. 
        Additionally, the trigger mode Gated is not allowed.
        """

        ctr_steps_written = 0
        goto_in_sequence = False
        for step, (wfm_tuple, seq_step) in enumerate(sequence_parameters, 1):

            try:
                next_step = sequence_parameters[step + 1][1]
            except IndexError:
                next_step = None

            if seq_step['go_to'] != -1:
                goto_in_sequence = True

            index = step - 1
            control = 0

            if index == 0:
                control = 0x1 << 28   # bit 28 (=0x10000000): mark as sequence start
            # in use case with external pattern jump, every segment with an address
            # defines a "sequence" (as defined in Keysight manual)
            if 'pattern_jump_address' in seq_step:
                control = 0x1 << 28

            if index + 1 == num_steps:
                control = 0x1 << 30   # bit 30: mark as sequence end
            if next_step:
                if 'pattern_jump_address' in next_step:
                    control = 0x1 << 30

            control += 0x1 << 24    # always enable markers

            seq_loop_count = 1
            if seq_step.repetitions == -1:
                # this is ugly, limits maximal waiting time. 1 Sa -> approx. 0.3 s
                seg_loop_count = 4294967295  # max value, todo: from constraints
            else:
                seg_loop_count = seq_step.repetitions + 1  # if repetitions = 0 then do it once
            seg_start_offset = 0    # play whole segement from start...
            seg_end_offset = 0xFFFFFFFF     # to end

            self.log.debug("For sequence table step {} with {} reps: control: {}".format(step,
                                                                                         seq_loop_count,
                                                                                         control))

            segment_id_ch1 = self.get_segment_id(self._remove_file_extension(wfm_tuple[0]), 1)
            segment_id_ch2 = self.get_segment_id(self._remove_file_extension(wfm_tuple[1]), 2)

            try:
                # creates all segments as data entries
                self.write(':STAB1:DATA {0}, {1}, {2}, {3}, {4}, {5}, {6}'
                           .format(index,
                                   control,
                                   seq_loop_count,
                                   seg_loop_count,
                                   segment_id_ch1,
                                   seg_start_offset,
                                   seg_end_offset))

                self.write(':STAB2:DATA {0}, {1}, {2}, {3}, {4}, {5}, {6}'
                           .format(index,
                                   control,
                                   seq_loop_count,
                                   seg_loop_count,
                                   segment_id_ch2,
                                   seg_start_offset,
                                   seg_end_offset))

                ctr_steps_written += 1

                self.log.debug("Writing seqtable entry {}: {}".format(index, step))

            except Exception as e:
                self.log.warning("Unknown error occured while writing to seq table: {}".format(str(e)))

        if goto_in_sequence and self.get_constraints().sequence_order == SequenceOrderOption.LINONLY:
            self.log.warning("Found go_to in step of sequence {}. Not supported and ignored.".format(name))

        return ctr_steps_written

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device incl. file extension.
        Keysight doesn't have mass memory, so name of sampled waveforms on pc.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """

        return self.query('MMEM:CAT?').replace('"','').replace("'","").split(",")[2::3]

    def get_sequence_names(self):
        """ Retrieve the names (without file extension) of all uploaded sequence on the device.
        Since Keysight has no mass storage: files on local pc.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        sequence_list = list()

        if not self.has_sequence_mode():
            return sequence_list

        # get only the files from the dir and skip possible directories
        log = os.listdir(self._assets_storage_path)
        file_list = [line for line in log if not os.path.isdir(line)]

        for filename in file_list:
            if filename.endswith(('.seq', '.seqx', '.sequence')):
                if filename not in sequence_list:
                    sequence_list.append(self._remove_file_extension(filename))
        return sequence_list

    def delete_waveform(self, waveform_name):
        """ Delete the waveform with name "waveform_name" from the device memory.

        @param str waveform_name: The name of the waveform to be deleted without _ch? postfix.
                                  Optionally a list of waveform names can be passed.

        @return list: a list of deleted waveform names.
        """
        if isinstance(waveform_name, str):
            waveform_name = [waveform_name]

        avail_waveforms = self.get_waveform_names()   # incl _ch?.bin postfix
        deleted_waveforms = list()

        for name in waveform_name:
            for waveform in avail_waveforms:
                if fnmatch(waveform.lower(), name.lower()+'_ch?.bin'):
                    # delete case insensitive
                    self.write(':MMEM:DEL "{0}"'.format(waveform))
                    deleted_waveforms.append(waveform)

        # clear the AWG if the deleted asset is the currently loaded asset
        if self.current_loaded_asset == waveform_name:
            self.clear_all()
        return deleted_waveforms

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory.

        @param str sequence_name: The name of the sequence to be deleted
                                  Optionally a list of sequence names can be passed.

        @return list: a list of deleted sequence names.
        """
        if isinstance(sequence_name, str):
            sequence_name = [sequence_name]

        avail_sequences = self.get_sequence_names()
        deleted_sequences = list()

        for name in sequence_name:
            for sequence in avail_sequences:
                if fnmatch(sequence, name+'_ch?.bin'):
                    deleted_sequences.append(sequence)

        # todo: get_sequence_names return no extension
        # todo: actually delete

        # clear the AWG if the deleted asset is the currently loaded asset
        if self.current_loaded_asset == sequence_name:
            self.clear_all()
        return deleted_sequences

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Will always return False for pulse generator hardware without interleave.
        """
        return False

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        @return bool: actual interleave status (True: ON, False: OFF)

        Note: After setting the interleave of the device, retrieve the
              interleave again and use that information for further processing.

        Unused for pulse generator hardware other than an AWG.
        """
        self.log.warning('Interleave mode not available for the AWG M8195A '
                         'Series!\n'
                         'Method call will be ignored.')
        return self.get_interleave()

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.write('*RST')
        self.write('*WAI')

        self._flag_segment_table_req_update = True

        return 0

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        return self._sequence_mode

    ################################################################################
    ###                         Non interface methods                            ###
    ################################################################################

    def write(self, command):
        """ Sends a command string to the device.

            @param string command: string containing the command

            @return int: error code (0:OK, -1:error)
        """
        bytes_written, enum_status_code = self.awg.write(command)

        if self._debug_check_all_commands:
            if 0 != self.check_dev_error():
                self.log.warn("Check failed after command: {}".format(command))

        return int(enum_status_code)

    def write_bin(self, command, values):
        """ Sends a command string to the device.

                    @param string command: string containing the command

                    @return int: error code (0:OK, -1:error)
        """
        self.awg.timeout = None
        bytes_written, enum_status_code = self.awg.write_binary_values(command, datatype='h', is_big_endian=False,
                                                                       values=values)
        self.awg.timeout = self._awg_timeout * 1000
        return int(enum_status_code)

    def query(self, question, force_no_check=False):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        ret = self.awg.query(question).strip().strip('"')
        if self._debug_check_all_commands and not force_no_check:
            if 0 != self.check_dev_error():
                self.log.warn("Check failed after query: {}".format(question))

        return ret

    def query_bin(self, question):

        return self.awg.query_binary_values(question, datatype='h', is_big_endian=False)

    def _is_awg_running(self):
        """
        Aks the AWG if the AWG is running
        @return: bool, (True: running, False: stoped)
        """
        # 0 No Output is running
        # 1 CH01 is running
        # 2 CH02 is running
        # 4 CH03 is running
        # 8 CH04 is running
        # run_state is sum of these

        run_state = self.query(':STAT:OPER:RUN:COND?')

        if int(run_state) == 0:
            return False
        else:
            return True

    def _is_output_on(self):
        """
        Asks the AWG if the outputs are on
        @return: bool, (True: Outputs are on, False: Outputs are switched off)
        """

        state = 0

        state += int(self.query(':OUTP1?'))
        state += int(self.query(':OUTP2?'))

        if int(state) == 0:
            return False
        else:
            return True

    def _get_all_channels(self):
        """
        Helper method to return a sorted list of all technically available channel descriptors
        (e.g. ['a_ch1', 'a_ch2', 'd_ch1', 'd_ch2'])

        @return list: Sorted list of channels
        """
        configs = self.get_constraints().activation_config
        if 'all' in configs:
            largest_config = configs['all']
        else:
            largest_config = list(configs.values())[0]
            for config in configs.values():
                if len(largest_config) < len(config):
                    largest_config = config
        return sorted(largest_config)

    def _get_all_analog_channels(self):
        """
        Helper method to return a sorted list of all technically available analog channel
        descriptors (e.g. ['a_ch1', 'a_ch2'])

        @return list: Sorted list of analog channels
        """
        return [chnl for chnl in self._get_all_channels() if chnl.startswith('a')]

    def _get_all_digital_channels(self):
        """
        Helper method to return a sorted list of all technically available digital channel
        descriptors (e.g. ['d_ch1', 'd_ch2'])

        @return list: Sorted list of digital channels
        """
        return [chnl for chnl in self._get_all_channels() if chnl.startswith('d')]

    def update_segment_table(self):
        segment_table_1 = self.read_segment_table(1)
        segment_table_2 = self.read_segment_table(2)
        self._segment_table[0] = segment_table_1
        self._segment_table[1] = segment_table_2

        self._flag_segment_table_req_update = False

        return segment_table_1, segment_table_2

    def get_segment_table(self, ch_num, force_from_local_copy=-1):

        if force_from_local_copy < 0:
            if self._flag_segment_table_req_update:
                self.log.debug("Local segment table seems out-of-date. Fetching.")
                segment_table_1, segment_table_2 = self.update_segment_table()
            else:
                segment_table_1, segment_table_2 = self._segment_table[0], self._segment_table[1]

        else:
            if force_from_local_copy == 1:
                if self._flag_segment_table_req_update:
                    self.log.warning("Forcing out-of-date local segment table that needs update")
                segment_table_1, segment_table_2 = self._segment_table[0], self._segment_table[1]

            elif force_from_local_copy == 0:
                segment_table_1, segment_table_2 = self.update_segment_table()
            else:
                raise ValueError("Unexpected input for force_from_local_copy: {}".format(force_from_local_copy))

        if ch_num == 1:
            return segment_table_1
        elif ch_num == 2:
            return segment_table_2
        else:
            raise ValueError("Unexpected channel number: {}".format(ch_num))

    def read_segment_table(self, ch_num):

        self.log.debug("Reading device segment table for ch {}".format(ch_num))

        names = self.get_loaded_assets_name(ch_num, mode='segment')
        ids = self.get_loaded_assets_id(ch_num, mode='segment')

        zipped = zip(ids, names)
        segment_table = []

        if len(names) != len(ids):
            self.log.error("Segment table on device seems unaligned.")
            return segment_table

        segment_table = [[x,y] for x,y in sorted(zipped)]

        return segment_table

    def get_segment_name(self, seg_id, ch_num):
        # awg 8190a has 2 separate sequencer per channel!

        segment_table = self.get_segment_table(ch_num)

        try:
            idx_id = [row[0] for row in segment_table].index(seg_id)
            name = [row[1] for row in segment_table][idx_id]

        except ValueError:
            self.log.warning("Couldn't find segment id {} in ch {}".format(seg_id, ch_num))
            return ''
        return name

    def get_segment_id(self, segment_waveform_name, ch_num):
        """
        Finds id of a given waveform name.
        :param segment_waveform_name: waveform name without (eg. .bin) extension
        :param ch_num: analog awg channel
        :return: -1 if not found
        """

        segment_table = self.get_segment_table(ch_num)

        try:
            # np.array would allow slicing, but list comprehension probably better performance
            idx_id = [row[1] for row in segment_table].index(segment_waveform_name)
            id = [row[0] for row in segment_table][idx_id]

        except ValueError:
            self.log.warning("Couldn't find waveform {} in ch {}".format(segment_waveform_name, ch_num))
            return -1
        return id

    def get_loaded_assets_num(self, ch_num, mode='segment'):
        if mode == 'segment':
            raw_str = self.query(':TRAC{:d}:CAT?'.format(ch_num))
        elif mode == 'sequence':
            raw_str = self.query(':SEQ{:d}:CAT?'.format(ch_num))
        else:
            self.log.warn("Unknown assets mode: {}".format(mode))
            return 0

        if raw_str == "0,0":
            return 0
        else:
            splitted = raw_str.rsplit(',')

            return int(len(splitted)/2)

    def get_loaded_assets_name(self, ch_num, mode='segment'):

        n_assets = self.get_loaded_assets_num(ch_num, mode)
        names = []
        for i in range(0, n_assets):

            if mode == 'segment':
                names.append(self.query(':TRAC{:d}:NAME? {:d}'.format(ch_num, i+1)))
            elif mode == 'sequence':
                names.append(self.query(':SEQ{:d}:NAME? {:d}'.format(ch_num, i)))
            else:
                self.log.warn("Unknown assets mode: {}".format(mode))
                return 0

        if n_assets == 0:
            return []
        else:
            return names

    def get_loaded_assets_id(self, ch_num, mode='segment'):

        if mode == 'segment':
            raw_str = self.query(':TRAC{:d}:CAT?'.format(ch_num))
        elif mode == 'sequence':
            raw_str = self.query(':SEQ{:d}:CAT?'.format(ch_num))
        else:
            self.log.warn("Unknown assets mode: {}".format(mode))
            return []
        n_assets = self.get_loaded_assets_num(ch_num, mode)

        if n_assets == 0:
            return []
        else:
            splitted = raw_str.rsplit(',')
            ids = [int(x) for x in splitted[0::2]]

            return ids

    def get_sequencer_state(self, ch_num):
        """
        Queries the state of the sequencer.
        :param ch_num: 1 or 2
        :return: state, sequence table id
                 state:
                 0: idle
                 1: waiting for trigger
                 2: running
                 3: waiting for advancement event
        """

        awg_mode = self.query("FUNC{:d}:MODE?".format(ch_num))
        if awg_mode == 'ARB':
            self.log.warning("Sequencer state is undefined in arb mode")
            return 0, 0

        bin_str = "{:b}".format(int(self.query("STAB{:d}:SEQ:STAT?".format(ch_num))))
        state = int(bin_str[0:2], 2)
        if state != 0:
            seq_table_id = int(bin_str[2:], 2)
        else:
            seq_table_id = 0

        return state, seq_table_id

    def set_trig_polarity(self, pol='pos'):
        if pol is "pos":
            self.write(":ARM:TRIG:SLOP POS")
        elif pol is "neg":
            self.write(":ARM:TRIG:SLOP NEG")
        elif pol is "both":
            self.write(":ARM:TRIG:SLOP EITH")

        else:
            self.log.error("Unknown trigger polarity: {}".format(pol))

    def _remove_file_extension(self, filename):
        """
        Removes filename, even if dot in filename.
        eg. rabi.1.bin -> rabi.1
            rabi.1 -> rabi
            rabi -> rabi
        :param filename:
        :return:
        """
        return filename.rsplit('.', 1)[0]

    def _create_dir(self, path):
        if not os.path.exists(path):
            try:
                os.mkdir(path)
                self.log.info("Folder was missing, so created: {}".format(path))
            except Exception as e:
                self.log.warning("Couldn't create folder: {}. {}".format(path, str(e)))

    def sequence_set_start_segment(self, seqtable_id):
        # todo: need to implement? alernatively shuffle sequuence while generating
        pass