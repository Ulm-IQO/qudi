import PyDAQmx as daq
import numpy as np

import abc
from core.meta import InterfaceMetaclass


class SerialInterface(metaclass=InterfaceMetaclass):
    """defines a device that can output bit patterns via a serial line"""
    _modtype = 'SerialInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def output_data(self, data):
        pass


class PatternJumpAdapter(SerialInterface):
    """
    General class implementing address output via NI card.
    Subclass to set params for a specific adapter.
    """

    strobe_ch = None  # implement in subclass '/dev1/port0/line25'
    data_ch = None  # implement in subclass '/dev1/port0/line17:24'

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.nitask_serial_out = None
        self.nitask_strobe_out = None

    def init_ni(self):

        if self.nitask_serial_out is not None or self.nitask_strobe_out is not None:
            self.stop_ni()

        self.nitask_serial_out = daq.TaskHandle()
        self.nitask_strobe_out = daq.TaskHandle()

        try:
            daq.DAQmxCreateTask('d_serial_out', daq.byref(self.nitask_serial_out))
        except daq.DuplicateTaskError:
            self.nitask_serial_out = self.recreate_nitask('d_serial_out', self.nitask_serial_out)

        daq.DAQmxCreateDOChan(self.nitask_serial_out, self.data_ch, "", daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxStartTask(self.nitask_serial_out)

        try:
            daq.DAQmxCreateTask('d_strobe_out', daq.byref(self.nitask_strobe_out))
        except daq.DuplicateTaskError:
            self.nitask_strobe_out = self.recreate_nitask('d_strobe_out', self.nitask_strobe_out)

        daq.DAQmxCreateDOChan(self.nitask_strobe_out, self.strobe_ch, "", daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxStartTask(self.nitask_strobe_out)

        #self.log.debug("Created ni tasks for outputting jump patterns.")

    def recreate_nitask(self, name, task):

        daq.DAQmxClearTask(task)
        new_task_handle = daq.TaskHandle()
        daq.DAQmxCreateTask(name, daq.byref(new_task_handle))

        return new_task_handle

    def stop_ni(self):
        daq.DAQmxClearTask(self.nitask_serial_out)
        daq.DAQmxClearTask(self.nitask_strobe_out)

    def output_data(self, data):
        digital_data = daq.c_uint32(data << 17)
        digital_read = daq.c_int32()    # dummy to feed to function
        n_samples = daq.c_int32(1)

        # value stays active at output
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

class PJAdapter_AWG70k(PatternJumpAdapter):
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
    data_ch =   '/dev1/port0/line17:24'


class PJAdapter_AWG8190A(PatternJumpAdapter):
    """
    Adapter for realising serial output of 13 data bits + 1 strobe bit.
    via NI PCIe 6323.
    Todo: currently data_select = 0, so only 13 bits addressable
    """

    strobe_ch = '/dev1/port0/line30'
    data_ch =   '/dev1/port0/line17:29'  # 12 bits
    data_select_ch = '/dev1/port0/line31'

if __name__ == '__main__':

    # for keysight m8190a jump port has:
    # data: 13 bits of jump address
    # select: 0: write address bits [0:12]/ 1: [13:18]
    # load: trigger/strobe the jump
    serial = PJAdapter_AWG8190A()
    serial.init_ni()

    import time
    for idx in range(20):
        serial.output_data(2)
        time.sleep(0.7)
    #serial.output_strobe()

    serial.stop_ni()