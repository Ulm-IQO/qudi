# -*- coding: utf-8 -*-
"""
This file contains the fgen interface.

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

import abc
from core.util.interfaces import InterfaceMetaclass


class FGenInterface(metaclass=InterfaceMetaclass):
    """
    Interface for functions generators following the IVI specification.
    """
    outputs = []

    @abc.abstractmethod
    def abort_generation(self):
        """
        Aborts a previously initiated signal generation. If the function generator
        is in the Output Generation State, this function moves the function
        generator to the Configuration State. If the function generator is already
        in the Configuration State, the function does nothing and returns Success.

        This specification requires that the user be able to configure the output
        of the function generator regardless of whether the function generator is
        in the Configuration State or the Generation State. This means that the
        user is not required to call Abort Generation prior to configuring the
        output of the function generator.

        Many function generators constantly generate an output signal, and do not
        require the user to abort signal generation prior to configuring the
        instrument. If a function generator's output cannot be aborted (i.e., the
        function generator cannot stop generating a signal) this function does
        nothing and returns Success.

        Some function generators require that the user abort signal generation
        prior to configuring the instrument. The specific drivers for these types
        of instruments must compensate for this restriction and allow the user to
        configure the instrument without requiring the user to call Abort
        Generation. For these types of instruments, there is often a significant
        performance increase if the user configures the output while the
        instrument is not generating a signal.

        The user is not required to call Abort Generation or Initiate Generation.
        Whether the user chooses to call these functions in an application
        program has no impact on interchangeability. The user can choose to use
        these functions if they want to optimize their application for instruments
        that exhibit increased performance when output configuration is performed
        while the instrument is not generating a signal.
        """
        pass

    @abc.abstractmethod
    def initiate_generation(self):
        """
        Initiates signal generation. If the function generator is in the
        Configuration State, this function moves the function generator to the
        Output Generation State. If the function generator is already in the
        Output Generation State, this function does nothing and returns Success.

        This specification requires that the instrument be in the Generation State
        after the user calls the Initialize or Reset functions. This specification
        also requires that the user be able to configure the output of the
        function generator regardless of whether the function generator is in the
        Configuration State or the Generation State. This means that the user is
        only required to call Initiate Generation if they abort signal generation
        by calling Abort Generation.

        Many function generators constantly generate an output signal, and do not
        require the user to abort signal generation prior to configuring the
        instrument. If a function generator's output cannot be aborted (i.e., the
        function generator cannot stop generating a signal) this function does
        nothing and returns Success.

        Some function generators require that the user abort signal generation
        prior to configuring the instrument. The specific drivers for these types
        of instruments must compensate for this restriction and allow the user to
        configure the instrument without requiring the user to call Abort
        Generation. For these types of instruments, there is often a significant
        performance increase if the user configures the output while the
        instrument is not generating a signal.

        The user is not required to call Abort Generation or Initiate Generation.
        Whether the user chooses to call these functions in an application
        program has no impact on interchangeability. The user can choose to use
        these functions if they want to optimize their application for instruments
        that exhibit increased performance when output configuration is performed
        while the instrument is not generating a signal.
        """
        pass


class OutputInterface(metaclass=InterfaceMetaclass):
    """
    Base IVI methods for all function generators related to an output.

    Implement as outputs[]
    """

    @property
    @abc.abstractmethod
    def name(self):
        """
        This property returns the physical name defined by the specific driver for
        the output channel that corresponds to the 0-based index that the user
        specifies. If the driver defines a qualified channel name, this property
        returns the qualified name. If the value that the user passes for the
        Index parameter is less than zero or greater than the value of Output
        Count, the property returns an empty string and returns an error.
        """
        pass

    @property
    @abc.abstractmethod
    def operation_mode(self):
        """
        Specifies how the function generator produces output on a channel.

        Values for operation_mode:

        * 'continuous'
        * 'burst'
        """
        pass

    @operation_mode.setter
    def operation_mode(self, value):
        pass

    @property
    @abc.abstractmethod
    def enabled(self):
        """
        If set to True, the signal the function generator produces appears at the
        output connector. If set to False, the signal the function generator
        produces does not appear at the output connector.
        """
        pass

    @enabled.setter
    def enabled(self, value):
        pass

    @property
    @abc.abstractmethod
    def impedance(self):
        """
        Specifies the impedance of the output channel. The units are Ohms.
        """
        pass

    @impedance.setter
    def impedance(self, value):
        pass

    @property
    @abc.abstractmethod
    def output_mode(self):
        """
        Determines how the function generator produces waveforms. This attribute
        determines which extension group's functions and attributes are used to
        configure the waveform the function generator produces.

        Values for output_mode:

        * 'function'
        * 'arbitrary'
        * 'sequence'
        """
        pass

    @output_mode.setter
    def output_mode(self, value):
        pass

    @property
    @abc.abstractmethod
    def reference_clock_source(self):
        """
        Specifies the source of the reference clock. The function generator
        derives frequencies and sample rates that it uses to generate waveforms
        from the reference clock.

        The source of the reference clock is a string. If an IVI driver supports a
        reference clock source and the reference clock source is listed in IVI-3.3
        Cross Class Capabilities Specification, Section 3, then the IVI driver
        shall accept the standard string for that reference clock. This attribute
        is case insensitive, but case preserving. That is, the setting is case
        insensitive but when reading it back the programmed case is returned. IVI
        specific drivers may define new reference clock source strings for
        reference clock sources that are not defined by IVI-3.3 Cross Class
        Capabilities Specification if needed.
        """
        pass

    @reference_clock_source.setter
    def reference_clock_source(self, value):
        pass


class StdFuncInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that can produce manufacturer-supplied periodic waveforms

    The IviFgenStdFunc Extension Group supports function generators that can produce manufacturer-supplied periodic
    waveforms. The user can modify properties of the waveform such as frequency, amplitude, DC offset, and phase offset.
    This extension affects instrument behavior when the Output Mode attribute is set to Output Function. Instrument
    vendors typically have different definitions for the waveform properties. In order to achieve a consistent waveform
    description between different instrument vendors, this specification provides waveform property definitions that
    must be followed when developing instrument drivers. The definitions for these waveform properties are given in
    the following list:
    Standard Waveform – The overall “shape” of one period of the standard waveform. This specification defines six
    waveform types: Sine, Square, Triangle, Ramp Up, Ramp Down, and DC.

    Implement as outputs[].standard_waveform
    """

    @property
    @abc.abstractmethod
    def amplitude(self):
        """
        Specifies the amplitude of the standard waveform the function generator
        produces. When the Waveform attribute is set to Waveform DC, this
        attribute does not affect signal output. The units are volts.
        """
        pass

    @amplitude.setter
    def amplitude(self, value):
        pass

    @property
    @abc.abstractmethod
    def dc_offset(self):
        """
        Specifies the DC offset of the standard waveform the function generator
        produces. If the Waveform attribute is set to Waveform DC, this attribute
        specifies the DC level the function generator produces. The units are
        volts.
        """
        pass

    @dc_offset.setter
    def dc_offset(self, value):
        pass

    @property
    @abc.abstractmethod
    def duty_cycle_high(self):
        """
        Specifies the duty cycle for a square waveform. This attribute affects
        function generator behavior only when the Waveform attribute is set to
        Waveform Square. The value is expressed as a percentage.
        """
        pass

    @duty_cycle_high.setter
    def duty_cycle_high(self, value):
        pass

    @property
    @abc.abstractmethod
    def start_phase(self):
        """
        Specifies the start phase of the standard waveform the function generator
        produces. When the Waveform attribute is set to Waveform DC, this
        attribute does not affect signal output. The units are degrees.
        """
        pass

    @start_phase.setter
    def start_phase(self, value):
        pass

    @property
    @abc.abstractmethod
    def frequency(self):
        """
        Specifies the frequency of the standard waveform the function generator
        produces. When the Waveform attribute is set to Waveform DC, this
        attribute does not affect signal output. The units are Hertz.
        """
        pass

    @frequency.setter
    def frequency(self, value):
        pass

    @property
    @abc.abstractmethod
    def waveform(self):
        """
        Specifies which standard waveform the function generator produces.

        Values for waveform:

        * 'sine'
        * 'square'
        * 'triangle'
        * 'ramp_up'
        * 'ramp_down'
        * 'dc'
        """
        pass

    @waveform.setter
    def waveform(self, value):
        pass

    def configure(self, waveform, amplitude, dc_offset, frequency, start_phase):
        """
        This function configures the attributes of the function generator that
        affect standard waveform generation. These attributes are the Waveform,
        Amplitude, DC Offset, Frequency, and Start Phase.

        When the Waveform parameter is set to Waveform DC, this function ignores
        the Amplitude, Frequency, and Start Phase parameters and does not set the
        Amplitude, Frequency, and Start Phase attributes.
        """
        pass


class ArbWfm_OutputsArbitrary_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that can produce arbitrary waveforms

    The IviFgenArbWfm Extension Group supports function generators capable of producing userdefined arbitrary waveforms.
    The user can modify parameters of the arbitrary waveform such as sample rate, waveform gain, and waveform offset.
    The IviFgenArbWfm extension group includes functions for creating, configuring, and generating arbitrary waveforms,
    and for returning information about arbitrary waveform creation. This extension affects instrument behavior when
    the Output Mode attribute is set to Output Arbitrary or Output Sequence. Before a function generator can produce an
    arbitrary waveform, the user must configure some signal generation properties. This specification provides
    definitions for arbitrary waveform properties that must be followed when developing instrument drivers. The
    definition of an arbitrary waveform and its properties are given in the following list:

    Arbitrary Waveform – A user-defined series of sequential data points, between –1.0 and 1.0 inclusive, that describe
                         an output waveform.
    Gain – The factor by which the function generator scales the arbitrary waveform data. For example, a gain value
           of 2.0 causes the waveform data to range from –2.0V to +2.0V.
    Offset – The value the function generator adds to the scaled arbitrary waveform data. For example, scaled arbitrary
             waveform data that ranges from –1.0V to +1.0V is generated from 0.0V to 2.0V when the end user specifies a
             waveform offset of 1.0V.

    Implement as outputs[].arbitrary

    See also: ArbWfm_ArbitraryWaveform_Interface
    """

    @property
    @abc.abstractmethod
    def gain(self):
        """
        Specifies the gain of the arbitrary waveform the function generator produces. This value is unitless.
        """
        pass

    @gain.setter
    def gain(self, value):
        pass

    @property
    @abc.abstractmethod
    def offset(self):
        """
        Specifies the offset of the arbitrary waveform the function generator produces. The units are volts.
        """
        pass

    @offset.setter
    def offset(self, value):
        pass

    @property
    @abc.abstractmethod
    def waveform(self):
        """
        Identifies which arbitrary waveform the function generator produces. You create arbitrary
        waveforms with the Create Arbitrary Waveform function. This function returns a handle that
        identifies the particular waveform. To configure the function generator to produce a specific
        waveform, set this attribute to the waveform’s handle.

        FIXME
        """
        pass

    @waveform.setter
    def waveform(self, value):
        pass

    def configure(self, waveform, gain, offset):
        """
        Configures the attributes of the function generator that affect arbitrary
        waveform generation. These attributes are the arbitrary waveform,
        gain, and offset.
        """
        pass


class ArbWfm_ArbitraryWaveform_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that can produce arbitrary waveforms.

    Implement as arbitrary.waveform

    See also: ArbWfm_OutputsArbitrary_Interface
    """
    @property
    @abc.abstractmethod
    def sample_rate(self):
        """
        Specifies the sample rate of the arbitrary waveforms the function
        generator produces. The units are samples per second.
        """
        pass

    @property
    @abc.abstractmethod
    def number_waveforms_max(self):
        """
        Returns the maximum number of arbitrary waveforms that the function
        generator allows.
        """
        pass

    @number_waveforms_max.setter
    def number_waveforms_max(self, value):
        pass

    @property
    @abc.abstractmethod
    def size_max(self):
        """
        Returns the maximum number of points the function generator allows in an
        arbitrary waveform.
        """
        pass

    @size_max.setter
    def size_max(self, value):
        pass

    @property
    @abc.abstractmethod
    def size_min(self):
        """
        Returns the minimum number of points the function generator allows in an
        arbitrary waveform.
        """
        pass

    @size_min.setter
    def size_min(self, value):
        pass

    @property
    @abc.abstractmethod
    def quantum(self):
        """
        The size of each arbitrary waveform shall be a multiple of a quantum
        value. This attribute returns the quantum value the function generator
        allows. For example, if this attribute returns a value of 8, all waveform
        sizes must be a multiple of 8.
        """
        pass

    @abc.abstractmethod
    def configure(self, waveform, gain, offset):
        """
        Configures the attributes of the function generator that affect arbitrary
        waveform generation. These attributes are the arbitrary waveform handle,
        gain, and offset.
        """
        pass

    @abc.abstractmethod
    def clear(self, waveform):
        """
        Removes a previously created arbitrary waveform from the function
        generator's memory and invalidates the waveform's handle.

        If the waveform cannot be cleared because it is currently being generated,
        or it is specified as part of an existing arbitrary waveform sequence,
        this function returns the Waveform In Use error.
        """
        pass

    @abc.abstractmethod
    def create(self):
        """
        Creates an arbitrary waveform from an array of data points. The function
        returns a handle that identifies the waveform. You pass a waveform handle
        to the Handle parameter of the Configure Arbitrary Waveform function to
        produce that waveform.
        """
        pass


class ArbFrequencyInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that can produce arbitrary waveforms with variable rate

    The IviFgenArbFrequency extension group supports function generators capable of producing arbitrary waveforms that
    allow the user to set the rate at which an entire waveform buffer is generated. In order to support this extension,
    a driver must first support the IviFgenArbWfm extension group. This extension uses the IviFgenArbWfm extension
    group’s attributes of Arbitrary Waveform Handle, Arbitrary Gain, and Arbitrary Offset to configure an arbitrary
    waveform.
    This extension affects instrument behavior when the Output Mode attribute is set to Output Arbitrary.

    Implement as outputs[].arbitrary
    """

    @property
    @abc.abstractmethod
    def frequency(self):
        """
        Specifies the rate in Hertz at which an entire arbitrary waveform is
        generated.
        """
        pass

    @frequency.setter
    def frequency(self, value):
        pass


class ArbSeq_ArbitrarySequence_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that can produce sequences of arbitrary waveforms

    The IviFgenArbSeq extension group supports function generators capable of producing sequences of arbitrary
    waveforms. In order to support this extension, a driver must first support the IviFgenArbWfm extension group.
    This extension uses the IviFgenArbWfm extension group's attributes of sample rate, gain, and offset to configure
    a sequence. The IviFgenArbSeq extension group includes functions for creating, configuring, and generating
    sequences, and for returning information about arbitrary sequence creation.

    This extension affects instrument behavior when the Output Mode attribute is set to Output Sequence.

    This specification defines an arbitrary sequence as a list of arbitrary waveforms to produce. Each waveform in the
    sequence is repeated a discrete number of times before producing the next waveform. When generating an arbitrary
    sequence, the waveform properties of Gain, Offset and Sample Rate defined in Section 6.1, IviFgenArbWfm Overview
    apply to all waveforms in the sequence.

    Implement as arbitrary.sequence

    See also: ArbSeq_Arbitrary_Interface, ArbSeq_OutputsArbitrarySequence_Interface
    """
    @property
    @abc.abstractmethod
    def number_sequences_max(self):
        """
        Returns the maximum number of arbitrary sequences that the function
        generator allows.
        """
        pass


    @property
    @abc.abstractmethod
    def loop_count_max(self):
        """
        Returns the maximum number of times that the function generator can repeat
        a waveform in a sequence.
        """
        pass

    @property
    @abc.abstractmethod
    def length_max(self):
        """
        Returns the maximum number of arbitrary waveforms that the function
        generator allows in an arbitrary sequence.
        """
        pass

    @property
    @abc.abstractmethod
    def length_min(self):
        """
        Returns the minimum number of arbitrary waveforms that the function
        generator allows in an arbitrary sequence.
        """
        pass

    @abc.abstractmethod
    def clear(self):
        """
        Removes a previously created arbitrary sequence from the function
        generator's memory and invalidates the sequence's handle.

        If the sequence cannot be cleared because it is currently being generated,
        this function returns the error Sequence In Use.
        """
        pass

    @abc.abstractmethod
    def configure(self, waveform, gain, offset):
        """
        Configures the attributes of the function generator that affect arbitrary
        sequence generation. These attributes are the arbitrary sequence handle,
        gain, and offset.
        """
        pass

    @abc.abstractmethod
    def create(self):
        """
        Creates an arbitrary waveform sequence from an array of waveform handles
        and a corresponding array of loop counts. The function returns a handle
        that identifies the sequence. You pass a sequence handle to the Handle
        parameter of the Configure Arbitrary Sequence function to produce that
        sequence.

        If the function generator cannot store any more arbitrary sequences, this
        function returns the error No Sequences Available.
        """
        pass


class ArbSeq_Arbitrary_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that can produce sequences of arbitrary waveforms

    Implement as arbitrary

    See also: ArbSeq_ArbitrarySequence_Interface, ArbSeq_OutputsArbitrarySequence_Interface
    """
    @abc.abstractmethod
    def clear_memory(self):
        """
        Removes all previously created arbitrary waveforms and sequences from the
        function generator's memory and invalidates all waveform and sequence
        handles.

        If a waveform cannot be cleared because it is currently being generated,
        this function returns the error Waveform In Use.

        If a sequence cannot be cleared because it is currently being generated,
        this function returns the error Sequence In Use.
        """
        pass


class ArbSeq_OutputsArbitrarySequence_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that can produce sequences of arbitrary waveforms

    Implement as outputs[].arbitrary.sequence

    See also: ArbSeq_ArbitrarySequence_Interface, ArbSeq_Arbitrary_Interface
    """
    @abc.abstractmethod
    def configure(self, waveform, gain, offset):
        """
        Configures the attributes of the function generator that affect arbitrary
        sequence generation. These attributes are the arbitrary sequence handle,
        gain, and offset.
        """
        pass


class TriggerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support triggering

    The IviFgenTrigger Extension Group supports function generators capable of configuring a trigger. This trigger
    source is used by other extension groups like IviFgenBurst to determine when to produce output generation. This
    extension group has been deprecated by the IviFgenStartTrigger Extension group. Drivers that support the
    IviFgenTrigger Extension group shall also support the IviFgenStartTrigger Extension group in order to be compliant
    with version 5.0 or later of the IviFgen class specification.

    This extension affects instrument behavior when the Operation Mode attribute is set to Operate Burst.

    Implement as outputs[].trigger
    """
    @property
    @abc.abstractmethod
    def source(self):
        """
        Specifies the trigger source. After the function generator receives a
        trigger from this source, it produces a signal.
        """
        pass

    @source.setter
    def source(self, value):
        pass


class StartTrigger_OutputsTriggerStart_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support start triggering

    The Extension Group supports function generators capable of configuring a
    start trigger. A start trigger initiates generation of a waveform or sequence.

    Setting the Start Trigger Source attribute to a value other than None enables the start trigger. To
    disable the start trigger, set the Start Trigger Source to None

    Implement as outputs[].trigger.start

    See also: StartTrigger_TriggerStart_Interface
    """
    @property
    @abc.abstractmethod
    def delay(self):
        """
        Specifies an additional length of time to delay from the start trigger to
        the first point in the waveform generation. The units are seconds.
        """
        pass

    @delay.setter
    def delay(self, value):
        pass

    @property
    @abc.abstractmethod
    def slope(self):
        """
        Specifies the slope of the trigger that starts the generator.

        Values for slope:

        * 'positive'
        * 'negative'
        * 'either'
        """
        pass

    @slope.setter
    def slope(self, value):
        pass

    @property
    @abc.abstractmethod
    def source(self):
        """
        Specifies the source of the start trigger.
        """
        pass

    @source.setter
    def source(self, value):
        pass

    @property
    @abc.abstractmethod
    def threshold(self):
        """
        Specifies the voltage threshold for the start trigger. The units are
        volts.
        """
        pass

    @threshold.setter
    def threshold(self, value):
        pass

    @abc.abstractmethod
    def configure(self, source, slope):
        """
        This function configures the start trigger properties.
        """
        pass


class StartTrigger_TriggerStart_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support start triggering

    Implement as trigger.start

    See also: StartTrigger_OutputsTriggerStart_Interface
    """

    @abc.abstractmethod
    def send_software_trigger(self):
        """
        This function sends a software-generated start trigger to the instrument.
        """
        pass


class StopTrigger_OutputsTriggerStop_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support stop triggering

    The Extension Group supports function generators capable of configuring a
    stop trigger. A stop trigger terminates any generation and has the same effect as calling the
    AbortGeneration function.
    Setting the Stop Trigger Source attribute to a value other than None enables the stop trigger. To
    disable the stop trigger, set the Stop Trigger Source to None.

    Implement as outputs[].trigger.stop

    See also: StopTrigger_TriggerStop_Interface
    """

    @property
    @abc.abstractmethod
    def delay(self):
        """
        Specifies an additional length of time to delay from the stop trigger to
        the termination of the generation. The units are seconds.
        """
        pass

    @delay.setter
    def delay(self, value):
        pass

    @property
    @abc.abstractmethod
    def slope(self):
        """
        Specifies the slope of the stop trigger.

        Values for slope:

        * 'positive'
        * 'negative'
        * 'either'
        """
        pass

    @slope.setter
    def slope(self, value):
        pass

    @property
    @abc.abstractmethod
    def source(self):
        """
        Specifies the source of the stop trigger.
        """
        pass

    @source.setter
    def source(self, value):
        pass

    @property
    @abc.abstractmethod
    def threshold(self):
        """
        Specifies the voltage threshold for the stop trigger. The units are volts.
        """
        pass

    @threshold.setter
    def threshold(self, value):
        pass

    @abc.abstractmethod
    def configure(self, source, slope):
        """
        This function configures the stop trigger properties.
        """
        pass


class StopTrigger_TriggerStop_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support stop triggering

    Implement as trigger.stop

    See also: StopTrigger_OutputsTriggerStop_Interface
    """

    @abc.abstractmethod
    def send_software_trigger(self):
        """
        This function sends a software-generated stop trigger to the instrument.
        """
        pass


class HoldTrigger_OutputsTriggerHold_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support hold triggering

    The Extension Group supports function generators capable of configuring a hold trigger. A hold trigger pauses
    generation. From the paused state, a resume trigger resumes generation; a stop trigger terminates generation;
    start trigger behavior is vendor defined.

    Setting the hold Trigger Source attribute to a value other than None enables the hold trigger. To
    disable the hold trigger, set the Hold Trigger Source to None.

    Implement as outputs[].trigger.hold

    See also: HoldTrigger_TriggerHold_Interface
    """

    @property
    @abc.abstractmethod
    def delay(self):
        """
        Specifies an additional length of time to delay from the hold trigger to
        the pause of the generation. The units are seconds.
        """
        pass

    @delay.setter
    def delay(self, value):
        pass

    @property
    @abc.abstractmethod
    def slope(self):
        """
        Specifies the slope of the hold trigger.

        Values for slope:

        * 'positive'
        * 'negative'
        * 'either'
        """
        pass

    @slope.setter
    def slope(self, value):
        pass

    @property
    @abc.abstractmethod
    def source(self):
        """
        Specifies the source of the hold trigger.
        """
        pass

    @source.setter
    def source(self, value):
        pass

    @property
    @abc.abstractmethod
    def threshold(self):
        """
        Specifies the voltage threshold for the hold trigger. The units are volts.
        """
        pass

    @threshold.setter
    def threshold(self, value):
        pass

    @abc.abstractmethod
    def configure(self, source, slope):
        """
        This function configures the hold trigger properties.
        """
        pass


class HoldTrigger_TriggerHold_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support hold triggering

    Implement as trigger.hold

    See also: HoldTrigger_OutputsTriggerHold_Interface
    """

    @abc.abstractmethod
    def send_software_trigger(self):
        """
        This function sends a software-generated hold trigger to the instrument.
        """
        pass


class ResumeTrigger_OutputsTriggerResume_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support resume triggering

    The Extension Group supports function generators capable of configuring a resume trigger. A resume trigger resumes
    generation after it has been paused by a hold trigger, starting with the next point.
    Setting the Resume Trigger Source attribute to a value other than None enables the resume trigger.
    To disable the resume trigger, set the Resume Trigger Source to None.

    Implement as outputs[].trigger.resume

    See also: ResumeTrigger_TriggerResume_Interface
    """

    @property
    @abc.abstractmethod
    def delay(self):
        """
        Specifies an additional length of time to delay from the resume trigger to
        the resumption of the generation. The units are seconds.
        """
        pass

    @delay.setter
    def delay(self, value):
        pass

    @property
    @abc.abstractmethod
    def slope(self):
        """
        Specifies the slope of the resume trigger.

        Values for slope:

        * 'positive'
        * 'negative'
        * 'either'
        """
        pass

    @property
    @abc.abstractmethod
    def source(self):
        """
        Specifies the source of the resume trigger.
        """
        pass

    @source.setter
    def source(self, value):
        pass

    @property
    @abc.abstractmethod
    def threshold(self):
        """
        Specifies the voltage threshold for the resume trigger. The units are
        volts.
        """
        pass

    @threshold.setter
    def threshold(self, value):
        pass

    @abc.abstractmethod
    def configure(self, source, slope):
        """
        This function configures the resume trigger properties.
        """
        pass


class ResumeTrigger_TriggerResume_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support resume triggering

    Implement as trigger.resume

    See also: ResumeTrigger_OutputsTriggerResume_Interface
    """

    @abc.abstractmethod
    def send_software_trigger(self):
        """
        This function sends a software-generated resume trigger to the instrument.
        """
        pass


class AdvanceTrigger_OutputsTriggerAdvance_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support advance triggering

    The Extension Group supports function generators capable of configuring
    an advance trigger. An advance trigger advances generation to the end of the current waveform,
    where generation proceeds according to the current configuration.
    Setting the Advance Trigger Source attribute to a value other than None enables the advance
    trigger. To disable the advance trigger, set the Advance Trigger Source to None.

    Implement as outputs[].trigger.advance

    See also: AdvanceTrigger_TriggerAdvance_Interface
    """

    @property
    @abc.abstractmethod
    def delay(self):
        """
        Specifies an additional length of time to delay from the advance trigger
        to the advancing to the end of the current waveform. Units are seconds.
        """
        pass

    @delay.setter
    def delay(self, value):
        pass

    @property
    @abc.abstractmethod
    def slope(self):
        """
        Specifies the slope of the advance trigger.

        Values for slope:

        * 'positive'
        * 'negative'
        * 'either'
        """
        pass

    @slope.setter
    def slope(self, value):
        pass

    @property
    @abc.abstractmethod
    def source(self):
        """ Specifies the source of the advance trigger. """
        pass

    @source.setter
    def source(self, value):
        pass

    @property
    @abc.abstractmethod
    def threshold(self):
        """ Specifies the voltage threshold for the advance trigger. The units are volts. """
        pass

    @threshold.setter
    def threshold(self, value):
        pass

    @abc.abstractmethod
    def configure(self, source, slope):
        """ This function configures the advance trigger properties. """
        pass


class AdvanceTrigger_TriggerAdvance_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support advance triggering

    Implement as trigger.advance

    See also: AdvanceTrigger_OutputsTriggerAdvance_Interface
    """

    @abc.abstractmethod
    def send_software_trigger(self):
        """ This function sends a software-generated advance trigger to the instrument. """
        pass


class InternalTriggerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support internal triggering

    The Extension Group supports function generators that can generate output
    based on an internally generated trigger signal. The user can configure the rate at which internal
    triggers are generated.
    This extension affects instrument behavior when the Trigger Source attribute is set to Internal
    Trigger.

    Implement as trigger
    """

    @property
    @abc.abstractmethod
    def internal_rate(self):
        """
        Specifies the rate at which the function generator's internal trigger
        source produces a trigger, in triggers per second.
        """
        pass

    @internal_rate.setter
    def internal_rate(self, value):
        pass


class SoftwareTriggerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support software triggering

    The Extension Group supports function generators that can generate
    output based on a software trigger signal. The user can send a software trigger to cause signal
    output to occur.
    This extension affects instrument behavior when the Trigger Source attribute is set to Software
    Trigger

    Implement in fgen class.
    """

    @abc.abstractmethod
    def send_software_trigger(self):
        """
        This function sends a software-generated trigger to the instrument. It is
        only applicable for instruments using interfaces or protocols which
        support an explicit trigger function. For example, with GPIB this function
        could send a group execute trigger to the instrument. Other
        implementations might send a ``*TRG`` command.

        Since instruments interpret a software-generated trigger in a wide variety
        of ways, the precise response of the instrument to this trigger is not
        defined. Note that SCPI details a possible implementation.

        This function should not use resources which are potentially shared by
        other devices (for example, the VXI trigger lines). Use of such shared
        resources may have undesirable effects on other devices.

        This function should not check the instrument status. Typically, the
        end-user calls this function only in a sequence of calls to other
        low-level driver functions. The sequence performs one operation. The
        end-user uses the low-level functions to optimize one or more aspects of
        interaction with the instrument. To check the instrument status, call the
        appropriate error query function at the conclusion of the sequence.

        The trigger source attribute must accept Software Trigger as a valid
        setting for this function to work. If the trigger source is not set to
        Software Trigger, this function does nothing and returns the error Trigger
        Not Software.
        """
        pass


class BurstOutputsInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support triggered burst output.

    The IviFgenBurst Extension Group supports function generators capable of generating a discrete number of waveform
    cycles based on a trigger. The trigger is configured with the IviFgenTrigger or IviFgenStartTrigger extension
    group. The user can specify the number of waveform cycles to generate when a trigger event occurs.
    For standard and arbitrary waveforms, a cycle is one period of the waveform. For arbitrary sequences, a cycle is
    one complete progression through the generation of all iterations of all waveforms in the sequence.
    This extension affects instrument behavior when the Operation Mode attribute is set to Operate Burst.

    Implement in outputs[]
    """

    @property
    @abc.abstractmethod
    def burst_count(self):
        """
        Specifies the number of waveform cycles that the function generator
        produces after it receives a trigger.
        """
        pass

    @burst_count.setter
    def burst_count(self, value):
        pass


class ModulateAM_OutputsAM_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support amplitude modulation

    The IviFgenModulateAM Extension Group supports function generators that can apply amplitude modulation to an output
    signal. The user can enable or disable amplitude modulation, and specify the source of the modulating waveform.
    If the function generator supports an internal modulating waveform source, the user can specify the waveform,
    frequency, and modulation depth. Amplitude modulation is accomplished by varying the amplitude of a carrier
    waveform according to the amplitude of a modulating waveform. The general equation for applying amplitude modulation
    to a waveform is,
    AM(t) = [M(t) + 1] x C(t),
    where C(t) is the carrier waveform, M(t) is the modulating waveform, and AM(t) is the modulated signal.

    This specification provides modulating waveform property definitions that must be followed when developing specific
    instrument drivers. The carrier waveform is defined as the waveform the function generator produces without any
    modulation. You configure the carrier waveform with the IviFgenStdFunc, IviFgenArbWfm, or IviFgenArbSeq capability
    groups.

    The modulating waveform is defined by the following properties:

    Waveform – The overall “shape” of one period of the modulating waveform. This specification defines five modulating
               waveforms: Sine, Square, Triangle, Ramp Up, and Ramp Down.
    Frequency – The number of modulating waveform cycles generated in one second.
    Modulation Depth – The extent to which the modulating waveform affects the amplitude of the carrier waveform. This
                       value is expressed as a percentage.

    At the maximum peak of the modulating waveform, the amplitude of the output signal is equal to
    (100.0 + Modulation Depth) percent of the carrier signal amplitude. At the minimum peak of the modulating waveform,
    the amplitude of the output signal is equal to (100.0 – Modulation Depth) percent of the carrier signal amplitude.
    At a modulation depth of 0 percent, the modulating waveform has no affect on the carrier waveform. At a modulation
    depth of 100 percent, the amplitude of the output signal varies between 0.0V and twice the amplitude of the carrier
    signal.

    Implement as outputs[].am

    See also: ModuleAM_AM_Interface
    """

    @property
    @abc.abstractmethod
    def enabled(self):
        """
        Specifies whether the function generator applies amplitude modulation to
        the signal that the function generator produces with the IviFgenStdFunc,
        IviFgenArbWfm, or IviFgenArbSeq capability groups. If set to True, the
        function generator applies amplitude modulation to the output signal. If
        set to False, the function generator does not apply amplitude modulation
        to the output signal.
        """
        pass

    @enabled.setter
    def enabled(self, value):
        pass

    @property
    @abc.abstractmethod
    def source(self):
        """
        Specifies the source of the signal that the function generator uses as the
        modulating waveform.

        This attribute affects instrument behavior only when the AM Enabled
        attribute is set to True.
        """
        pass

    @source.setter
    def source(self, value):
        pass


class ModulateAM_AM_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support amplitude modulation

    Implement as am

    See also: ModulateAM_OutputsAM_Interface
    """

    @property
    @abc.abstractmethod
    def internal_depth(self):
        """
        Specifies the extent of modulation the function generator applies to the
        carrier waveform when the AM Source attribute is set to AM Internal. The
        unit is percentage.

        This attribute affects the behavior of the instrument only when the AM
        ource attribute is set to AM Internal.
        """
        pass

    @internal_depth.setter
    def internal_depth(self,value):
        pass

    @property
    @abc.abstractmethod
    def internal_frequency(self):
        """
        Specifies the frequency of the internal modulating waveform source. The
        units are Hertz.

        This attribute affects the behavior of the instrument only when the AM
        ource attribute is set to AM Internal.
        """
        pass

    @internal_frequency.setter
    def internal_frequency(self, value):
        pass

    @property
    @abc.abstractmethod
    def internal_waveform(self):
        """
        Specifies the waveform of the internal modulating waveform source.

        This attribute affects the behavior of the instrument only when the AM
        ource attribute is set to AM Internal.

        Values for internal_waveform:

        * 'sine'
        * 'square'
        * 'triangle'
        * 'ramp_up'
        * 'ramp_down'
        * 'dc'
        """
        pass

    @internal_waveform.setter
    def internal_waveform(self, value):
        pass

    @abc.abstractmethod
    def configure_internal(self, modulation_depth, waveform, frequency):
        """
        Configures the attributes that control the function generator's internal
        amplitude modulating waveform source. These attributes are the modulation
        depth, waveform, and frequency.
        """
        pass


class ModulateFM_OutputsFM_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support frequency modulation

    The IviFgenModulateFM Extension Group supports function generators that can apply frequency modulation to an
    output signal. The user can enable or disable frequency modulation, and specify the source of the modulating
    waveform. If the function generator supports an internal modulating waveform source, the user can specify the
    waveform type, frequency, and peak frequency deviation.
    Frequency modulation is accomplished by varying the frequency of a carrier waveform according to the amplitude of
    a modulating waveform. The general equation for a frequency modulated waveform is,
    FM(t) = C[t + (M(t))],
    where C(t) is the carrier waveform, M(t) is the modulating waveform, and FM(t) is the frequency modulated signal.

    This specification provides modulating waveform property definitions that must be followed when developing specific
    instrument drivers. The carrier waveform is defined as the waveform the function generator produces without any
    modulation. You configure the carrier waveform with the IviFgenStdFunc, IviFgenArbWfm, or IviFgenArbSeq capability
    groups. The modulating waveform is defined by the following properties:

    Waveform Type – The overall “shape” of one period of the modulating waveform. This specification defines five
                    modulation waveform types: Sine, Square, Triangle, Ramp Up, and Ramp Down.
    Frequency – The number of modulating waveform cycles generated in one second.
    Peak Frequency Deviation – The variation of frequency the modulating waveform applies to the carrier waveform.
                               This value is expressed in hertz. At 0 hertz deviation, the modulating waveform has no
                               effect on the carrier waveform. As frequency deviation increases, the frequency
                               variation in the modulated waveform increases.

    At the maximum peak of the modulating waveform, the frequency of the output signal is equal to the frequency of the
    carrier signal plus the Peak Frequency Deviation. At the minimum peak of the modulating waveform, the frequency of
    the output signal is equal to the frequency of the carrier signal minus the Peak Frequency Deviation.

    Implement as outputs[].fm.

    See also: ModulateFM_FM_Interface
    """

    @property
    @abc.abstractmethod
    def enabled(self):
        """
        Specifies whether the function generator applies amplitude modulation to
        the carrier waveform. If set to True, the function generator applies
        frequency modulation to the output signal. If set to False, the function
        generator does not apply frequency modulation to the output signal.
        """
        pass

    @enabled.setter
    def enabled(self, value):
        pass

    @property
    @abc.abstractmethod
    def source(self):
        """
        Specifies the source of the signal that the function generator uses as the
        modulating waveform.

        This attribute affects instrument behavior only when the FM Enabled
        attribute is set to True.
        """
        pass

    @source.setter
    def source(self, value):
        pass


class ModulateFM_FM_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support frequency modulation

    Implement as fm.

    See also: ModulateFM_OutputsFM_Interface
    """

    @property
    @abc.abstractmethod
    def internal_deviation(self):
        """
        Specifies the maximum frequency deviation, in Hertz, that the function
        generator applies to the carrier waveform when the FM Source attribute is
        set to FM Internal.

        This attribute affects the behavior of the instrument only when the FM
        Source attribute is set to FM Internal.
        """
        pass

    @internal_deviation.setter
    def internal_deviation(self, value):
        pass

    @property
    @abc.abstractmethod
    def internal_frequency(self):
        """
        Specifies the frequency of the internal modulating waveform source. The
        units are hertz.

        This attribute affects the behavior of the instrument only when the FM
        Source attribute is set to FM Internal.
        """
        pass

    @internal_frequency.setter
    def internal_frequency(self, value):
        pass

    @property
    @abc.abstractmethod
    def internal_waveform(self):
        """
        Specifies the waveform of the internal modulating waveform source.

        This attribute affects the behavior of the instrument only when the FM
        Source attribute is set to FM Internal.

        Values for internal_waveform:

        * 'sine'
        * 'square'
        * 'triangle'
        * 'ramp_up'
        * 'ramp_down'
        * 'dc'
        """
        pass

    @internal_waveform.setter
    def internal_waveform(self, value):
        pass

    @abc.abstractmethod
    def configure_internal(self, deviation, waveform, frequency):
        """
        Configures the attributes that control the function generator's internal frequency modulating
        waveform source. These attributes are the modulation peak deviation, waveform, and frequency.

        This attribute affects instrument behavior only when the FM Enabled
        attribute is set to True.
        """
        pass


class SampleClockInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support external sample clocks

    The IviFgenSampleClock extension group supports arbitrary waveform generators with the ability to use (or provide)
    an external sample clock. Note that when using an external sample clock, the Arbitrary Sample Rate attribute must
    be set to the corresponding frequency of the external sample clock.

    Implement as sample_clock.
    """

    @property
    @abc.abstractmethod
    def source(self):
        """
        Specifies the clock used for the waveform generation. Note that when using
        an external sample clock, the Arbitrary Sample Rate attribute must be set
        to the corresponding frequency of the external sample clock.
        """
        pass

    @source.setter
    def source(self, value):
        pass

    @property
    @abc.abstractmethod
    def output_enabled(self):
        """ Specifies whether or not the sample clock appears at the sample clock output of the generator. """
        pass

    @output_enabled.setter
    def output_enabled(self, value):
        pass


class TerminalConfigurationInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support single ended or differential output selection

    Implement as mixin to outputs[].
    """

    @property
    @abc.abstractmethod
    def terminal_configuration(self):
        """
        Determines whether the generator will run in single-ended or differential
        mode, and whether the output gain and offset values will be analyzed
        based on single-ended or differential operation.

        Values for terminal_configuration:

        * 'single_ended'
        * 'differential'
        """
        pass

    @terminal_configuration.setter
    def terminal_configuration(self, value):
        pass


class ArbChannelWfm_OutputsArbitrary_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support user-defined arbitrary waveform generation

    The IviFgenArbChannelWfm Extension Group supports single channel and multichannel function generators capable of
    producing user-defined arbitrary waveforms for specific output channels. The IviFgenArbChannelWfm extension group
    includes functions for creating, configuring, and generating arbitrary waveforms.

    Implement as mixin to outputs[].arbitrary

    See also: ArbChannelWfm_ArbitraryWaveform_Interface
    """

    @abc.abstractmethod
    def create_waveform(self):
        """
        Creates a channel-specific arbitrary waveform and returns a handle that
        identifies that waveform. You pass a waveform handle as the waveformHandle
        parameter of the Configure Arbitrary Waveform function to produce that
        waveform. You also use the handles this function returns to create a
        sequence of arbitrary waveforms with the Create Arbitrary Sequence
        function.

        If the instrument has multiple channels, it is possible to create
        multi-channel waveforms: the channel names are passed as a
        comma-separated list of channel names, and the waveform arrays are
        concatenated into a single array. In this case, all waveforms must be of
        the same length.

        If the function generator cannot store any more arbitrary waveforms, this
        function returns the error No Waveforms Available.
        """
        pass


class ArbChannelWfm_ArbitraryWaveform_Interface(metaclass=InterfaceMetaclass):
    """
    The IviFgenArbChannelWfm Extension Group supports single channel and multichannel function generators capable
    of producing user-defined arbitrary waveforms for specific output channels. The IviFgenArbChannelWfm extension
    group includes functions for creating, configuring, and generating arbitrary waveforms.

    Implement as arbitrary.waveform

    See also: ArbChannelWfm_OutputsArbitrary_Interface
    """
    def create_channel_waveform(self, channel_names, waveforms):
        """
        Creates a channel-specific arbitrary waveform and returns a handle that
        identifies that waveform. You pass a waveform handle as the waveformHandle
        parameter of the Configure Arbitrary Waveform function to produce that
        waveform. You also use the handles this function returns to create a
        sequence of arbitrary waveforms with the Create Arbitrary Sequence
        function.

        If the instrument has multiple channels, it is possible to create
        multi-channel waveforms: the channel names are passed as a
        comma-separated list of channel names, and the waveform arrays are
        concatenated into a single array. In this case, all waveforms must be of
        the same length.

        If the function generator cannot store any more arbitrary waveforms, this
        function returns the error No Waveforms Available.
        """
        pass


class ArbWfmBinary_OutputsArbitraryWaveform_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support user-defined arbitrary binary waveform generation

    The IviFgenArbWfmBinary Extension Group supports multichannel function generators capable of producing user-defined
    arbitrary waveforms that can be specified in binary format. The IviFgenArbWfmBinary extension group includes
    functions for creating, configuring, and generating arbitrary waveforms.

    Implement as outputs[].arbitrary.waveform

    See also: ArbWfmBinary_Arbitrary_Interface, ArbWfmBinary_ArbitraryWaveform_Interface
    """
    @abc.abstractmethod
    def create_channel_waveform_int16(self, waveform):
        """
        Creates a channel-specific arbitrary waveform and returns a handle that
        identifies that waveform. Data is passed in as 16-bit binary data. If the
        arbitrary waveform generator supports formats less than 16 bits, call the
        BinaryAlignment property to determine whether to left or right justify the
        data before passing it to this call. You pass a waveform handle as the
        waveformHandle parameter of the Configure Arbitrary Waveform function to
        produce that waveform. You also use the handles this function returns to
        create a sequence of arbitrary waveforms with the Create Arbitrary
        Sequence function.

        If the instrument has multiple channels, it is possible to create
        multi-channel waveforms: the channel names are passed as a
        comma-separated list of channel names, and the waveform arrays
        are concatenated into a single array. In this case, all waveforms
        must be of the same length.

        If the function generator cannot store any more arbitrary waveforms, this
        function returns the error No Waveforms Available.
        """
        pass

        @abc.abstractmethod
        def create_channel_waveform_int32(self, waveform):
            """
            Creates a channel-specific arbitrary waveform and returns a handle that
            identifies that waveform. Data is passed in as 32-bit binary data. If the
            arbitrary waveform generator supports formats less than 32 bits, call the
            BinaryAlignment property to determine whether to left or right justify the
            data before passing it to this call. You pass a waveform handle as the
            waveformHandle parameter of the Configure Arbitrary Waveform function to
            produce that waveform. You also use the handles this function returns to
            create a sequence of arbitrary waveforms with the Create Arbitrary
            Sequence function.

            If the instrument has multiple channels, it is possible to create
            multi-channel waveforms: the channel names are passed as a
            comma-separated list of channel names, and the waveform arrays
            are concatenated into a single array. In this case, all waveforms
            must be of the same length.

            If the function generator cannot store any more arbitrary waveforms, this
            function returns the error No Waveforms Available.
            """
            pass


class ArbWfmBinary_Arbitrary_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support user-defined arbitrary binary waveform generation

    The IviFgenArbWfmBinary Extension Group supports multichannel function generators capable of producing user-defined
    arbitrary waveforms that can be specified in binary format. The IviFgenArbWfmBinary extension group includes
    functions for creating, configuring, and generating arbitrary waveforms.

    Implement as arbitrary

    See also: ArbWfmBinary_OutputsArbitraryWaveform_Interface, ArbWfmBinary_ArbitraryWaveform_Interface
    """
    @property
    @abc.abstractmethod
    def binary_alignment(self):
        """
        Identifies whether the arbitrary waveform generator treats binary data
        provided to the Create Channel Arbitrary Waveform Int16 or Create Channel
        Arbitrary Waveform Int32 functions as left-justified or right-justified.
        Binary Alignment is only relevant if the generator supports bit-depths
        less than the size of the binary data type of the create waveform function
        being used. For a 16-bit or a 32-bit generator, this function can return
        either value.
        """
        pass

    @binary_alignment.setter
    def binary_alignment(self, value):
        pass

    @property
    @abc.abstractmethod
    def sample_bit_resolution(self):
        """
        Returns the number of significant bits that the generator supports in an
        arbitrary waveform. Together with the binary alignment, this allows the
        user to know the range and resolution of the integers in the waveform.
        """
        pass

    @sample_bit_resolution.setter
    def sample_bit_resolution(self, value):
        pass


class ArbWfmBinary_ArbitraryWaveform_Interface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support user-defined arbitrary binary waveform generation

    The IviFgenArbWfmBinary Extension Group supports multichannel function generators capable of producing user-defined
    arbitrary waveforms that can be specified in binary format. The IviFgenArbWfmBinary extension group includes
    functions for creating, configuring, and generating arbitrary waveforms.

    Implement as arbitrary.waveform

    See also: ArbWfmBinary_OutputsArbitraryWaveform_Interface, ArbWfmBinary_Arbitrary_Interface
    """
    def create_channel_waveform_int16(self, channel_names, waveforms):
        """
        Creates a channel-specific arbitrary waveform and returns a handle that
        identifies that waveform. Data is passed in as 16-bit binary data. If the
        arbitrary waveform generator supports formats less than 16 bits, call the
        BinaryAlignment property to determine whether to left or right justify the
        data before passing it to this call. You pass a waveform handle as the
        waveformHandle parameter of the Configure Arbitrary Waveform function to
        produce that waveform. You also use the handles this function returns to
        create a sequence of arbitrary waveforms with the Create Arbitrary
        Sequence function.

        If the instrument has multiple channels, it is possible to create
        multi-channel waveforms: the channel names are passed as a
        comma-separated list of channel names, and the waveform arrays
        are concatenated into a single array. In this case, all waveforms
        must be of the same length.

        If the function generator cannot store any more arbitrary waveforms, this
        function returns the error No Waveforms Available.
        """
        pass

    def create_channel_waveform_int32(self, channel_names, waveforms):
        """
        Creates a channel-specific arbitrary waveform and returns a handle that
        identifies that waveform. Data is passed in as 32-bit binary data. If the
        arbitrary waveform generator supports formats less than 32 bits, call the
        BinaryAlignment property to determine whether to left or right justify the
        data before passing it to this call. You pass a waveform handle as the
        waveformHandle parameter of the Configure Arbitrary Waveform function to
        produce that waveform. You also use the handles this function returns to
        create a sequence of arbitrary waveforms with the Create Arbitrary
        Sequence function.

        If the instrument has multiple channels, it is possible to create
        multi-channel waveforms: the channel names are passed as a
        comma-separated list of channel names, and the waveform arrays
        are concatenated into a single array. In this case, all waveforms
        must be of the same length.

        If the function generator cannot store any more arbitrary waveforms, this
        function returns the error No Waveforms Available.
        """
        pass


class DataMarkerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support output of particular waveform data bits as markers

    The IviFgenDataMarker Extension Group supports arbitrary waveform generators that can output particular bits of
    waveform data as a marker output. The user can choose which bit (the 2nd bit for example) gets output, where the
    output goes, and various analog characteristics of the marker output. Data markers are repeated capabilities to
    allow the user to output multiple bits to different ouputs simultaneously. The user can also use the DataMask
    property to ensure that the data marker does not get output with the main waveform output.

    Setting the Data Marker Destination attribute to a value other than None enables the data marker. To disable the
    data marker, set the Data Marker Destination to None.

    Implement in a list as data_markers[].
    """
    @property
    @abc.abstractmethod
    def name(self):
        """
        This attribute returns the repeated capability identifier defined by
        specific driver for the data marker that corresponds to the index that the
        user specifies. If the driver defines a qualified Data Marker name, this
        property returns the qualified name.

        If the value that the user passes for the Index parameter is less than
        zero or greater than the value of the Data Marker Count, the attribute
        returns an empty string for the value and returns an error.
        """
        pass

    @name.setter
    def name(self, value):
        pass

    @property
    @abc.abstractmethod
    def amplitude(self):
        """
        Specifies the amplitude of the data marker output. The units are volts.
        """
        pass

    @amplitude.setter
    def amplitude(self, value):
        pass

    @property
    @abc.abstractmethod
    def bit_position(self):
        """
        Specifies the bit position of the binary representation of the waveform
        data that will be output as a data marker. A value of 0 indicates the
        least significant bit.
        """
        pass

    @bit_position.setter
    def bit_position(self, value):
        pass

    @property
    @abc.abstractmethod
    def delay(self):
        """
        Specifies the amount of delay applied to the data marker output with
        respect to the analog data output. A value of zero indicates the marker is
        aligned with the analog data output.  The units are seconds.
        """
        pass

    @delay.setter
    def delay(self, value):
        pass

    @property
    @abc.abstractmethod
    def destination(self):
        """
        Specifies the destination terminal for the data marker output.
        """
        pass

    @destination.setter
    def destination(self, value):
        pass

    @property
    @abc.abstractmethod
    def polarity(self):
        """
        Specifies the polarity of the data marker output.

        Values for polarity:

        * 'active_high'
        * 'active_low'
        """
        pass

    @polarity.setter
    def polarity(self, value):
        pass

    @property
    @abc.abstractmethod
    def source_channel(self):
        """
        Specifies the channel whose data bit will be output as a marker.
        """
        pass

    @source_channel.setter
    def source_channel(self, value):
        pass

    @abc.abstractmethod
    def configure(self, source_channel, bit_position, destination):
        """
        Configures some of the common data marker attributes: source channel, bit position and destination
        """
        pass

    @abc.abstractmethod
    def clear(self):
        """
        Disables all of the data markers by setting their Data Marker Destination
        attribute to None.
        """
        pass


class ArbDataMaskInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support masking of waveform data bits

    The IviFgenArbDataMask extension group supports arbitrary waveform generators with the ability to mask out
    bits of the output data.

    Implement as mixing to arbitrary
    """
    @property
    @abc.abstractmethod
    def data_mask(self):
        """
        Determines which bits of the output data are masked out. This is
        especially useful when combined with Data Markers so that the bits
        embedded with the data to be used for markers are not actually output by
        the generator.

        A value of 1 for a particular bit indicates that the data bit should be
        output. A value of 0 indicates that the data bit should be masked out. For
        example, if the value of this property is 0xFFFFFFFF (all bits are 1), no
        masking is applied.
        """
        pass

    @data_mask.setter
    def data_mask(self, value):
        pass


class SparseMarkerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support output of markers associated with output data samples

    The IviFgenSparseMarker Extension Group supports arbitrary waveform generators that can output signals, known as
    markers, associated with specified samples in the output data. Unlike data markers, sparse markers are not stored
    as part of the waveform data, but rather provided as a list of particular samples of the waveform on which the
    marker should be output. The user can choose which waveform and sample number the output is associated with,
    where the output goes, and various analog characteristics of the marker output. Sparse markers are repeated
    capabilities to allow the user to specify multiple markers to different outputs simultaneously.

    Setting the Sparse Marker Destination attribute to a value other than None enables the sparse marker. To disable
    the sparse marker, set the Sparse Marker Destination to None.

    Implement as sparse_markers[]
    """
    @property
    @abc.abstractmethod
    def name(self):
        """
        This attribute returns the repeated capability identifier defined by
        specific driver for the sparse marker that corresponds to the index that
        the user specifies. If the driver defines a qualified Sparse Marker name,
        this property returns the qualified name.

        If the value that the user passes for the Index parameter is less than one
        or greater than the value of the Sparse Marker Count, the attribute
        returns an empty string for the value and returns an error.
        """
        pass

    @name.setter
    def name(self, value):
        pass

    @property
    @abc.abstractmethod
    def amplitude(self):
        """
        Specifies the amplitude of the sparse marker output. The units are volts.
        """
        pass

    @amplitude.setter
    def amplitude(self, value):
        pass

    @property
    @abc.abstractmethod
    def delay(self):
        """
        Specifies the amount of delay applied to the sparse marker output with
        respect to the analog data output. A value of zero indicates the marker is
        aligned with the analog data output. The units are seconds.
        """
        pass

    @delay.setter
    def delay(self, value):
        pass

    @property
    @abc.abstractmethod
    def destination(self):
        """
        Specifies the destination terminal for the sparse marker output.
        """
        pass

    @property
    @abc.abstractmethod
    def polarity(self):
        """
        Specifies the polarity of the sparse marker output.

        Values for polarity:

        * 'active_high'
        * 'active_low'
        """
        pass

    @polarity.setter
    def polarity(self, value):
        pass

    @property
    @abc.abstractmethod
    def waveform_handle(self):
        """
        Specifies the waveform whose indexes the sparse marker refers to.
        """
        pass

    @waveform_handle.setter
    def waveform_handle(self, value):
        pass

    @abc.abstractmethod
    def configure(self, waveform_handle, indexes, destination):
        """
        Configures some of the common sparse marker attributes.
        """
        pass

    @abc.abstractmethod
    def get_indexes(self):
        """
        Gets the coerced indexes associated with the sparse marker. These indexes
        are specified by either the Configure SparseMarker function or the Set
        Sparse Marker Indexes function.
        """
        pass

    @abc.abstractmethod
    def set_indexes(self, indexes):
        """
        Sets the indexes associated with the sparse marker. These indexes may be
        coerced by the driver. Use the Get Sparse Marker Indexes function to find
        the coerced values.
        """
        pass

    @abc.abstractmethod
    def clear(self):
        """
        Disables all of the sparse markers by setting their Sparse Marker
        Destination attribute to None.
        """
        pass


class ArbSeqDepthInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for function generators that support producing sequences of sequences of waveforms

    The IviFgenArbSeqDepth extension group supports arbitrary waveform generators supporting IviFgenArbSeq and that
    are capable of producing sequences of sequences of arbitrary waveforms.

    Implement as arbitrary.sequence
    """
    @property
    @abc.abstractmethod
    def depth_max(self):
        """
        Returns the maximum sequence depth - that is, the number of times a
        sequence can include other sequences recursively. A depth of zero
        indicates the generator supports waveforms only. A depth of 1 indicates a
        generator supports sequences of waveforms, but not sequences of sequences.
        A depth of 2 or greater indicates that the generator supports sequences of
        sequences. Note that if the MaxSequenceDepth is 2 or greater, the driver
        must return unique handles for waveforms and sequences so that a sequence
        may contain both waveform and sequence handles.
        """
        pass
