from abc import ABCMeta
from enum import Enum

class InterfaceMetaclass(ABCMeta):
    """
    Metaclass for interfaces.
    """
    pass


class PulserInterface(metaclass=InterfaceMetaclass):
    pass

class ScalarConstraint:
    """
    Constraint definition for a scalar variable hardware parameter.
    """
    def __init__(self, min=0.0, max=0.0, step=0.0, default=0.0, unit=''):
        # allowed minimum value for parameter
        self.min = min
        # allowed maximum value for parameter
        self.max = max
        # allowed step size for parameter value changes (for spinboxes etc.)
        self.step = step
        # the default value for the parameter
        self.default = default
        # the unit of the parameter value(optional)
        self.unit = unit
        return


class PulserConstraints():
    def __init__(self):
        # sample rate, i.e. the time base of the pulser
        self.sample_rate = ScalarConstraint(unit='Hz')
        # The peak-to-peak amplitude and voltage offset of the analog channels
        self.a_ch_amplitude = ScalarConstraint(unit='Vpp')
        self.a_ch_offset = ScalarConstraint(unit='V')
        # Low and high voltage level of the digital channels
        self.d_ch_low = ScalarConstraint(unit='V')
        self.d_ch_high = ScalarConstraint(unit='V')
        # length of the created waveform in samples
        self.waveform_length = ScalarConstraint(unit='Samples')
        # number of waveforms/sequences to put in a single asset (sequence mode)
        self.waveform_num = ScalarConstraint(unit='#')
        self.sequence_num = ScalarConstraint(unit='#')
        self.subsequence_num = ScalarConstraint(unit='#')
        # Sequence parameters
        self.sequence_steps = ScalarConstraint(unit='#', min=0)
        self.repetitions = ScalarConstraint(unit='#')
        self.event_triggers = list()
        self.flags = list()

        self.activation_config = dict()
        self.sequence_option = None

class SequenceOption(Enum):
    """
    Different options of the sequence mode in the pulser device.
    """
    NON = 0  # No sequence mode, only waveforms can be used
    OPTIONAL = 1  # Pulser can either work with waveforms directly or use sequences for the output
    FORCED = 2  # Output is only allowed for sequences. Waveforms might still be uploaded but not played.
