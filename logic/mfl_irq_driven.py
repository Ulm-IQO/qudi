from logic.generic_logic import GenericLogic
from hardware.national_instruments_x_series import NationalInstrumentsXSeries

from core.module import Connector, StatusVar

class MFL_IRQ_Driven(GenericLogic):

    _modclass = 'mfl_irq_driven'
    _modtype = 'logic'

    # this class requires a NI X Series counter
    counter = Connector(interface='SlowCounterInterface')

    _epoch_done_trig_ch = StatusVar('_epoch_done_trig_ch', 'dev1/port0/line0')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.i_epoch = 0
        self.jumptable = None

        self.nicard = None
        self.serial = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.nicard = self.counter()
        if not isinstance(self.nicard, NationalInstrumentsXSeries):
            self.log.warning("Config defines not supported counter of type {} for MFL logic, not NI X Series.",
                             type(self.nicard))

        self.serial = PatternJumpAdapter()
        self.serial.init_ni()

    def on_deactivate(self):
        """ """
        self.serial.stop_ni()

    def set_jumptable(self, jumptable_dict, tau_list):
        #self._jumptable = {'name': [], 'idx_seqtable': [], 'jump_address': []}

        jumptable_dict['tau'] = tau_list
        self.jumptable = jumptable_dict

    def get_jump_address(self, idx_epoch):
        adr = self.jumptable['jump_address'][idx_epoch]
        name = self.jumptable['name'][idx_epoch]
        self.log.debug("Resolving jump address {} to segment{} for epooh {}.".format(adr, name, idx_epoch))

        return adr

    def setup_new_run(self):
        self.i_epoch = 0
        self.nicard.register_callback_on_change_detection(self._epoch_done_trig_ch,
                                                          self.__cb_func_epoch_done, edges=[True, False])

    def output_jump_pattern(self, jump_address):
        self.serial.output_data(jump_address)

    def iterate_mfl(self):
        self.i_epoch += 1

    def get_ramsey_result(self):
        mes = pulsedmasterlogic.pulsedmeasurementlogic()
        # get data at least once, even if timer to analyze not fired yet
        mes.manually_pull_data()

        x = mes.signal_data[0]
        y = mes.signal_data[1]

        return (x, y)

    def calc_tau_from_posterior(self):
        return 10e-1

    def calc_jump_addr(self, tau):
        return 1

    def __cb_func_epoch_done(self, taskhandle, signalID, callbackData):
        self.log.debug("MFL callback invoked in epoch {}".format(self.i_epoch))

        z = self.get_ramsey_result()

        self.iterate_mfl()
        tau = self.calc_tau_from_posterior()
        addr = self.calc_jump_addr(tau)
        self.output_jump_pattern(addr)

        return 0


import abc
from core.util.interfaces import InterfaceMetaclass
class SerialInterface(metaclass=InterfaceMetaclass):
    """defines a device that can output bit patterns via a serial line"""
    _modtype = 'SerialInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def output_data(self, data):
        pass

import PyDAQmx as daq
import numpy as np
class PatternJumpAdapter(SerialInterface):
    """
    Adapter for realising serial output of 8 data bits + 1 strobe bit
    via NI PCIe 6323.
    uint32 written to NI. Translation to 8 bits:
    Lowest numbered bit on data ch is LSB, highest bit is MSB.
    Eg. line17: MSB, line23: LSB.
    data_in         line17... 23
                    |          |
    data = 1    =>  100...     0
    data = 128  =>  000...     1
    """
    strobe_ch = '/dev1/port0/line25'
    data_ch = '/dev1/port0/line17:24'

    def __init__(self, data_ch=None, strobe_ch=None):
        super().__init__()
        self.nitask_serial_out = None
        self.nitask_strobe_out = None

    def init_ni(self):
        self.nitask_serial_out = daq.TaskHandle()
        self.nitask_strobe_out = daq.TaskHandle()

        daq.DAQmxCreateTask('DigitalSerialOut', daq.byref(self.nitask_serial_out))
        daq.DAQmxCreateDOChan(self.nitask_serial_out, self.data_ch, "", daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxStartTask(self.nitask_serial_out)

        daq.DAQmxCreateTask('DigitalStrobeOut', daq.byref(self.nitask_strobe_out))
        daq.DAQmxCreateDOChan(self.nitask_strobe_out, self.strobe_ch, "", daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxStartTask(self.nitask_strobe_out)


    def stop_ni(self):
        daq.DAQmxStopTask(self.nitask_serial_out)
        daq.DAQmxClearTask(self.nitask_serial_out)
        daq.DAQmxStopTask(self.nitask_strobe_out)
        daq.DAQmxClearTask(self.nitask_strobe_out)

    def output_data(self, data):
        digital_data = daq.c_uint32(data << 17)
        digital_read = daq.c_int32()    # dummy to feed to function
        n_samples = daq.c_int32(1)

        # value stays active at ouput
        daq.DAQmxWriteDigitalU32(self.nitask_serial_out, n_samples, True,
                                 0, daq.DAQmx_Val_GroupByChannel,
                                 np.array(digital_data), digital_read, None)

        self.output_strobe()

    def output_bit(self, idx_bit, high=True):
        """
        :param idx_bit: counted from 0 from low to high. idx_bit=0 -> line17, idx_bit=7 -> line 24
        :param high:
        :return:
        """
        digital_data = daq.c_uint32(0x1 << idx_bit + 17)
        digital_low = daq.c_uint32(0x0)
        digital_read = daq.c_int32()  # dummy to feed to function
        n_samples = daq.c_int32(1)

        if high:
            daq.DAQmxWriteDigitalU32(self.nitask_serial_out, n_samples, True,
                                     0, daq.DAQmx_Val_GroupByChannel,
                                     np.array(digital_data), digital_read, None)
        else:
            daq.DAQmxWriteDigitalU32(self.nitask_serial_out, n_samples, True,
                                     0, daq.DAQmx_Val_GroupByChannel,
                                     np.array(digital_low), digital_read, None)


    def output_strobe(self):
        digital_strobe = daq.c_uint32(0xffffffff)
        digital_low = daq.c_uint32(0x0)
        digital_read = daq.c_int32()  # dummy to feed to function
        n_samples = daq.c_int32(1)

        daq.DAQmxWriteDigitalU32(self.nitask_strobe_out, n_samples, True,
                                 0, daq.DAQmx_Val_GroupByChannel,
                                 np.array(digital_strobe), digital_read, None)
        daq.DAQmxWriteDigitalU32(self.nitask_strobe_out, n_samples, True,
                                 0, daq.DAQmx_Val_GroupByChannel,
                                 np.array(digital_low), digital_read, None)

