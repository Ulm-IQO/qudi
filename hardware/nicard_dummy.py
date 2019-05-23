import numpy as np
import re

"""
extends slow_counter_dummy to be compatible to setup3 script_logic_essentials.py
"""

from core.module import Base, ConfigOption
from interface.slow_counter_interface import SlowCounterInterface
from hardware.slow_counter_dummy import SlowCounterDummy

class NicardDummy(SlowCounterDummy):

    _modtype = 'NICard_Dummy'
    _modclass = 'hardware'


    def reset_hardware(self):
        pass

    def digital_channel_switch(self, channel_name, mode=True):
        pass

