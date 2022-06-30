from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass

class NIQtAOInterface(metaclass=InterfaceMetaclass):

    @abstract_interface_method
    def set_up_clock(self,clock_frequency=None, clock_channel=None, scanner=False, idle=False):

        pass

    @abstract_interface_method
    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       counter_buffer=None):

        pass

    @abstract_interface_method
    def close_counter(self, scanner=False):

        pass

    @abstract_interface_method
    def close_clock(self, scanner=False):
        pass

    @abstract_interface_method
    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        pass

    @abstract_interface_method
    def set_up_scanner(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       scanner_ao_channels=None):
        pass

    @abstract_interface_method
    def scanner_set_position(self, x=None):
        pass

    @abstract_interface_method
    def get_scanner_position(self):
        pass

    @abstract_interface_method
    def scan_line(self, line_path=None, pixel_clock=False):
        pass

    @abstract_interface_method
    def close_scanner(self):
        pass

    @abstract_interface_method
    def close_scanner_clock(self):
        pass