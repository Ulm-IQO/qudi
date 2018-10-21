# -*- coding: utf-8 -*-
"""
This file contains the implementation of the pythonIvi interface for function generators.

The main class is ::PythonIVIFGen.::

Example configuration

hardware:
    awg5002c:
        module.Class: 'fgen.python_ivi_fgen.PythonIviFGen'
        driver: 'ivi.tektronix.tektronixAWG5002C.tektronixAWG5002C'
        uri: 'TCPIP0::192.168.1.1::INSTR'


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

from interface import fgen_ivi_interface
from ..python_ivi_base import PythonIviBase
from .._ivi_core import Namespace

import abc
import inspect
from qtpy.QtCore import QObject
from qtpy.QtCore import Signal
import ivi.fgen


class QtInterfaceMetaclass(type(QObject), abc.ABCMeta):
    pass


class _FGen(fgen_ivi_interface.FGenIviInterface):
    """
    Interface for functions generators following the IVI specification.
    """
    generation_aborted = Signal()
    generation_initiated = Signal()

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
        self.driver.abort_generation()
        self.generation_aborted.emit()

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
        self.driver.initiate_generation()
        self.generation_initiated.emit()

    class outputs(fgen_ivi_interface.FGenIviInterface.outputs):
        operation_mode_changed = Signal(str)
        enabled_changed = Signal(bool)
        impedance_changed = Signal(int)
        output_mode_changed = Signal(str)
        reference_clock_source_changed = Signal(str)

        @property
        def name(self):
            """
            This property returns the physical name defined by the specific driver for
            the output channel that corresponds to the 0-based index that the user
            specifies. If the driver defines a qualified channel name, this property
            returns the qualified name. If the value that the user passes for the
            Index parameter is less than zero or greater than the value of Output
            Count, the property returns an empty string and returns an error.
            """
            return self.root.driver.outputs[self.index].name

        @property
        def operation_mode(self):
            """
            Specifies how the function generator produces output on a channel.

            Values for operation_mode:

            * 'continuous'
            * 'burst'
            """
            return self.root.driver.outputs[self.index].operation_mode

        @operation_mode.setter
        def operation_mode(self, value):
            self.root.driver.outputs[self.index].operation_mode = value
            self.operation_mode_changed.emit(value)

        @property
        def enabled(self):
            """
            If set to True, the signal the function generator produces appears at the
            output connector. If set to False, the signal the function generator
            produces does not appear at the output connector.
            """
            return self.root.driver.outputs[self.index].enabled

        @enabled.setter
        def enabled(self, value):
            self.root.driver.outputs[self.index].enabled = value
            self.enabled_changed.emit(value)

        @property
        def impedance(self):
            """
            Specifies the impedance of the output channel. The units are Ohms.
            """
            return self.root.driver.outputs[self.index].impedance

        @impedance.setter
        def impedance(self, value):
            self.root.driver.outputs[self.index].impedance = value
            self.impedance_changed.emit(value)

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
            return self.root.driver.outputs[self.index].output_mode

        @output_mode.setter
        def output_mode(self, value):
            self.root.driver.outputs[self.index].output_mode = value
            self.output_mode_changed.emit(value)

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
            return self.root.driver.outputs[self.index].reference_clock_source

        @reference_clock_source.setter
        def reference_clock_source(self, value):
            self.root.driver.outputs[self.index].reference_clock_source = value
            self.reference_clock_source_changed.emit(value)


# ************************ EXTENSIONS **************************************************************

class StdFuncExtension(fgen_ivi_interface.StdFuncExtensionInterface):
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
    """
    class outputs(fgen_ivi_interface.StdFuncExtensionInterface.outputs):
        class standard_waveform(QObject, fgen_ivi_interface.StdFuncExtensionInterface.outputs.standard_waveform,
                                metaclass=QtInterfaceMetaclass):
            amplitude_changed = Signal(float)
            dc_offset_changed = Signal(float)
            duty_cycle_high_changed = Signal(float)
            start_phase_changed = Signal(float)
            frequency_changed = Signal(float)
            waveform_changed = Signal(str)

            @property
            def amplitude(self):
                """
                Specifies the amplitude of the standard waveform the function generator
                produces. When the Waveform attribute is set to Waveform DC, this
                attribute does not affect signal output. The units are volts.
                """
                return self.root.driver.outputs[self.parent_namespace.index].standard_waveform.amplitude

            @amplitude.setter
            def amplitude(self, value):
                self.root.driver.outputs[self.parent_namespace.index].standard_waveform.amplitude = value
                self.amplitude_changed.emit(value)

            @property
            def dc_offset(self):
                """
                Specifies the DC offset of the standard waveform the function generator
                produces. If the Waveform attribute is set to Waveform DC, this attribute
                specifies the DC level the function generator produces. The units are
                volts.
                """
                return self.root.driver.outputs[self.parent_namespace.index].standard_waveform.dc_offset

            @dc_offset.setter
            def dc_offset(self, value):
                self.root.driver.outputs[self.parent_namespace.index].standard_waveform.dc_offset = value
                self.dc_offset_changed.emit(value)

            @property
            @abc.abstractmethod
            def duty_cycle_high(self):
                """
                Specifies the duty cycle for a square waveform. This attribute affects
                function generator behavior only when the Waveform attribute is set to
                Waveform Square. The value is expressed as a percentage.
                """
                return self.root.driver.outputs[self.parent_namespace.index].standard_waveform.duty_cycle_high

            @duty_cycle_high.setter
            def duty_cycle_high(self, value):
                self.root.driver.outputs[self.parent_namespace.index].standard_waveform.duty_cycle_high = value
                self.duty_cycle_high_changed.emit(value)

            @property
            @abc.abstractmethod
            def start_phase(self):
                """
                Specifies the start phase of the standard waveform the function generator
                produces. When the Waveform attribute is set to Waveform DC, this
                attribute does not affect signal output. The units are degrees.
                """
                return self.root.driver.outputs[self.parent_namespace.index].standard_waveform.start_phase

            @start_phase.setter
            def start_phase(self, value):
                self.root.driver.outputs[self.parent_namespace.index].standard_waveform.start_phase = value
                self.start_phase_changed.emit(value)

            @property
            @abc.abstractmethod
            def frequency(self):
                """
                Specifies the frequency of the standard waveform the function generator
                produces. When the Waveform attribute is set to Waveform DC, this
                attribute does not affect signal output. The units are Hertz.
                """
                return self.root.driver.outputs[self.parent_namespace.index].standard_waveform.frequency

            @frequency.setter
            def frequency(self, value):
                self.root.driver.outputs[self.parent_namespace.index].standard_waveform.frequency = value
                self.frequency_changed.emit(value)

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
                return self.root.driver.outputs[self.parent_namespace.index].standard_waveform.waveform

            @waveform.setter
            def waveform(self, value):
                self.root.driver.outputs[self.parent_namespace.index].standard_waveform.waveform = value
                self.waveform_changed.emit(value)

            def configure(self, waveform, amplitude, dc_offset, frequency, start_phase):
                """
                This function configures the attributes of the function generator that
                affect standard waveform generation. These attributes are the Waveform,
                Amplitude, DC Offset, Frequency, and Start Phase.

                When the Waveform parameter is set to Waveform DC, this function ignores
                the Amplitude, Frequency, and Start Phase parameters and does not set the
                Amplitude, Frequency, and Start Phase attributes.
                """
                self.root.driver.outputs[self.parent_namespace.index].standard_waveform.configure(waveform,
                                                                                                  amplitude,
                                                                                                  dc_offset,
                                                                                                  frequency,
                                                                                                  start_phase)


class ArbWfmExtension(fgen_ivi_interface.ArbWfmExtensionInterface):
    """
    Extension IVI methods for function generators that can produce arbitrary waveforms

    The IviFgenArbWfm Extension Group supports function generators capable of producing userdefined
    arbitrary waveforms. The user can modify parameters of the arbitrary waveform such as sample
    rate, waveform gain, and waveform offset. The IviFgenArbWfm extension group includes functions
    for creating, configuring, and generating arbitrary waveforms, nd for returning information
    about arbitrary waveform creation. This extension affects instrument behavior when the Output
    Mode attribute is set to Output Arbitrary or Output Sequence. Before a function generator can
    produce an arbitrary waveform, the user must configure some signal generation properties. This
    specification provides definitions for arbitrary waveform properties that must be followed when
    developing instrument drivers. The definition of an arbitrary waveform and its properties are
    given in the following list:

    Gain – The factor by which the function generator scales the arbitrary waveform data. For
           example, a gain value of 2.0 causes the waveform data to range from –2.0V to +2.0V.
    Offset – The value the function generator adds to the scaled arbitrary waveform data. For
             example, scaled arbitrary waveform data that ranges from –1.0V to +1.0V is generated
             from 0.0V to 2.0V when the end user specifies a waveform offset of 1.0V.
    """
    class outputs(fgen_ivi_interface.ArbWfmExtensionInterface.outputs):
        class arbitrary(fgen_ivi_interface.ArbWfmExtensionInterface.outputs.arbitrary):
            gain_changed = Signal(float)
            offset_changed = Signal(float)

            @property
            def gain(self):
                """
                Specifies the gain of the arbitrary waveform the function generator produces. This value is
                unitless.
                """
                return self.root.driver.outputs[self.parent_namespace.index].arbitrary.gain

            @gain.setter
            def gain(self, value):
                self.root.driver.outputs[self.parent_namespace.index].arbitrary.gain = value
                self.gain_changed.emit(value)

            @property
            def offset(self):
                """
                Specifies the offset of the arbitrary waveform the function generator produces. The units
                are volts.
                """
                return self.root.driver.outputs[self.parent_namespace.index].arbitrary.offset

            @offset.setter
            def offset(self, value):
                self.root.driver.outputs[self.parent_namespace.index].arbitrary.offset = value
                self.offset_changed.emit(value)

            def configure(self, waveform, gain, offset):
                """
                Configures the attributes of the function generator that affect arbitrary
                waveform generation. These attributes are the arbitrary waveform,
                gain, and offset.
                """
                self.root.driver.outputs[self.parent_namespace.index].arbitrary.configure(waveform, gain, offset)

            class waveform(fgen_ivi_interface.ArbWfmExtensionInterface.outputs.arbitrary.waveform):
                @property
                def handle(self):
                    """
                    Identifies which arbitrary waveform the function generator produces. You create arbitrary
                    waveforms with the Create Arbitrary Waveform function. This function returns a handle that
                    identifies the particular waveform. To configure the function generator to produce a
                    specific waveform, set this attribute to the waveform’s handle.
                    """
                    return self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].arbitrary.waveform.handle

                @handle.setter
                def handle(self, value):
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].arbitrary.waveform.handle = value


    class arbitrary(fgen_ivi_interface.ArbWfmExtensionInterface.arbitrary):
        sample_rate_changed = Signal(int)

        @property
        def sample_rate(self):
            """
            Specifies the sample rate of the arbitrary waveforms the function
            generator produces. The units are samples per second.
            """
            return self.root.driver.arbitrary.sample_rate

        @sample_rate.setter
        def sample_rate(self, value):
            self.root.driver.arbitrary.sample_rate = value
            self.sample_rate_changed.emit(value)

        class waveform(fgen_ivi_interface.ArbWfmExtensionInterface.arbitrary.waveform):
            @property
            def number_waveforms_max(self):
                """
                Returns the maximum number of arbitrary waveforms that the function
                generator allows.
                """
                return self.root.driver.arbitrary.waveform.number_waveforms_max

            @property
            @abc.abstractmethod
            def size_max(self):
                """
                Returns the maximum number of points the function generator allows in an
                arbitrary waveform.
                """
                return self.root.driver.arbitrary.waveform.size_max

            @property
            @abc.abstractmethod
            def size_min(self):
                """
                Returns the minimum number of points the function generator allows in an
                arbitrary waveform.
                """
                return self.root.driver.arbitrary.waveform.size_min

            @property
            @abc.abstractmethod
            def quantum(self):
                """
                The size of each arbitrary waveform shall be a multiple of a quantum
                value. This attribute returns the quantum value the function generator
                allows. For example, if this attribute returns a value of 8, all waveform
                sizes must be a multiple of 8.
                """
                return self.root.driver.arbitrary.waveform.quantum

            @abc.abstractmethod
            def clear(self, waveform):
                """
                Removes a previously created arbitrary waveform from the function
                generator's memory and invalidates the waveform's handle.

                If the waveform cannot be cleared because it is currently being generated,
                or it is specified as part of an existing arbitrary waveform sequence,
                this function returns the Waveform In Use error.
                """
                self.root.driver.arbitrary.waveform.clear(waveform)

            @abc.abstractmethod
            def create(self, data):
                """
                Creates an arbitrary waveform from an array of data points. The function
                returns a handle that identifies the waveform. You pass a waveform handle
                to the Handle parameter of the Configure Arbitrary Waveform function to
                produce that waveform.
                """
                return self.root.driver.arbitrary.waveform.create(data)


class ArbFrequencyExtension(fgen_ivi_interface.ArbFrequencyExtensionInterface):
    """
    Extension IVI methods for function generators that can produce arbitrary waveforms with variable rate

    The IviFgenArbFrequency extension group supports function generators capable of producing arbitrary waveforms that
    allow the user to set the rate at which an entire waveform buffer is generated. In order to support this extension,
    a driver must first support the IviFgenArbWfm extension group. This extension uses the IviFgenArbWfm extension
    group’s attributes of Arbitrary Waveform Handle, Arbitrary Gain, and Arbitrary Offset to configure an arbitrary
    waveform.
    This extension affects instrument behavior when the Output Mode attribute is set to Output Arbitrary.
    """
    class outputs(fgen_ivi_interface.ArbFrequencyExtensionInterface.outputs):
        class arbitrary(fgen_ivi_interface.ArbFrequencyExtensionInterface.outputs.arbitrary):
            frequency_changed = Signal(float)

            @property
            def frequency(self):
                """
                Specifies the rate in Hertz at which an entire arbitrary waveform is
                generated.
                """
                return self.root.driver.outputs[self.parent_namespace.index].arbitrary.frequency

            @frequency.setter
            def frequency(self, value):
                self.root.driver.outputs[self.parent_namespace.index].arbitrary.frequency = value
                self.frequency_changed.emit(value)



class ArbSeqExtension(fgen_ivi_interface.ArbSeqExtensionInterface):
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
    """
    class arbitrary(fgen_ivi_interface.ArbSeqExtensionInterface.arbitrary):
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
            self.root.driver.arbitrary.clear_memory()

        class sequence(fgen_ivi_interface.ArbSeqExtensionInterface.arbitrary.sequence):
            @property
            def number_sequences_max(self):
                """
                Returns the maximum number of arbitrary sequences that the function
                generator allows.
                """
                return self.root.driver.arbitrary.sequence.number_sequences_max

            @property
            def loop_count_max(self):
                """
                Returns the maximum number of times that the function generator can repeat
                a waveform in a sequence.
                """
                return self.root.driver.arbitrary.sequence.loop_count_max

            @property
            def length_max(self):
                """
                Returns the maximum number of arbitrary waveforms that the function
                generator allows in an arbitrary sequence.
                """
                return self.root.driver.arbitrary.sequence.length_max

            @property
            def length_min(self):
                """
                Returns the minimum number of arbitrary waveforms that the function
                generator allows in an arbitrary sequence.
                """
                return self.root.driver.arbitrary.sequence.length_min

            def clear(self, sequence_handle):
                """
                Removes a previously created arbitrary sequence from the function
                generator's memory and invalidates the sequence's handle.

                If the sequence cannot be cleared because it is currently being generated,
                this function returns the error Sequence In Use.
                """
                self.root.driver.arbitrary.sequence.clear(sequence_handle)

            def create(self, waveform_handles):
                """
                Creates an arbitrary waveform sequence from an array of waveform handles
                and a corresponding array of loop counts. The function returns a handle
                that identifies the sequence. You pass a sequence handle to the Handle
                parameter of the Configure Arbitrary Sequence function to produce that
                sequence.

                If the function generator cannot store any more arbitrary sequences, this
                function returns the error No Sequences Available.
                """
                return self.root.driver.arbitrary.sequence.create(waveform_handles)

    class outputs:
        class arbitrary:
            @Namespace
            class sequence(QObject, fgen_ivi_interface.ArbSeqExtensionInterface.outputs.arbitrary.sequence,
                           metaclass=QtInterfaceMetaclass):
                def configure(self, sequence_handle, gain, offset):
                    """
                    Configures the attributes of the function generator that affect arbitrary
                    sequence generation. These attributes are the arbitrary sequence handle,
                    gain, and offset.
                    """
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].arbitrary.sequence.configure(sequence_handle,
                                                                                                   gain,
                                                                                                   offset)


class TriggerExtension(fgen_ivi_interface.TriggerExtensionInterface):
    """
    Extension IVI methods for function generators that support triggering

    The IviFgenTrigger Extension Group supports function generators capable of configuring a trigger. This trigger
    source is used by other extension groups like IviFgenBurst to determine when to produce output generation. This
    extension group has been deprecated by the IviFgenStartTrigger Extension group. Drivers that support the
    IviFgenTrigger Extension group shall also support the IviFgenStartTrigger Extension group in order to be compliant
    with version 5.0 or later of the IviFgen class specification.

    This extension affects instrument behavior when the Operation Mode attribute is set to Operate Burst.
    """
    class outputs:
        class trigger(fgen_ivi_interface.TriggerExtensionInterface.outputs.trigger):
            source_changed = Signal(str)

            @property
            def source(self):
                """
                Specifies the trigger source. After the function generator receives a
                trigger from this source, it produces a signal.
                """
                return self.root.driver.outputs[self.parent_namespace.index].trigger.source

            @source.setter
            def source(self, value):
                self.root.driver.outputs[self.parent_namespace.index].trigger.source = value
                self.source_changed.emit(value)


class StartTriggerExtension(fgen_ivi_interface.StartTriggerExtensionInterface):
    """
    Extension IVI methods for function generators that support start triggering

    The Extension Group supports function generators capable of configuring a
    start trigger. A start trigger initiates generation of a waveform or sequence.

    Setting the Start Trigger Source attribute to a value other than None enables the start trigger. To
    disable the start trigger, set the Start Trigger Source to None
    """
    class outputs:
        class trigger:
            @Namespace
            class start(QObject,
                        fgen_ivi_interface.StartTriggerExtensionInterface.outputs.trigger.start,
                        metaclass=QtInterfaceMetaclass):
                delay_changed = Signal(float)
                slope_changed = Signal(str)
                source_changed = Signal(str)
                threshold_changed = Signal(float)

                @property
                def delay(self):
                    """
                    Specifies an additional length of time to delay from the start trigger to
                    the first point in the waveform generation. The units are seconds.
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.start.delay

                @delay.setter
                def delay(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.start.delay = value
                    self.delay_changed.emit(value)

                @property
                def slope(self):
                    """
                    Specifies the slope of the trigger that starts the generator.

                    Values for slope:

                    * 'positive'
                    * 'negative'
                    * 'either'
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.start.slope

                @slope.setter
                def slope(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.start.slope = value
                    self.slope_changed.emit(value)

                @property
                def source(self):
                    """
                    Specifies the source of the start trigger.
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.start.source

                @source.setter
                def source(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.start.source = value
                    self.source_changed.emit(value)

                @property
                def threshold(self):
                    """
                    Specifies the voltage threshold for the start trigger. The units are
                    volts.
                    """
                    return self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.start.threshold

                @threshold.setter
                def threshold(self, value):
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.start.threshold = value
                    self.threshold_changed.emit(value)

                def configure(self, source, slope):
                    """
                    This function configures the start trigger properties.
                    """
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.start.configure(source, slope)

    class trigger:
        class start(QObject,
                    fgen_ivi_interface.StartTriggerExtensionInterface.trigger.start,
                    metaclass=QtInterfaceMetaclass):
            def send_software_trigger(self):
                """
                This function sends a software-generated start trigger to the instrument.
                """
                self.root.driver.trigger.start.send_software_trigger()


class StopTriggerExtension(fgen_ivi_interface.StopTriggerExtensionInterface):
    """
    Extension IVI methods for function generators that support stop triggering

    The Extension Group supports function generators capable of configuring a
    stop trigger. A stop trigger terminates any generation and has the same effect as calling the
    AbortGeneration function.
    Setting the Stop Trigger Source attribute to a value other than None enables the stop trigger. To
    disable the stop trigger, set the Stop Trigger Source to None.
    """
    class outputs:
        class trigger:
            class stop(QObject,
                       fgen_ivi_interface.StopTriggerExtensionInterface.outputs.trigger.stop,
                       metaclass=QtInterfaceMetaclass):
                delay_changed = Signal(float)
                slope_changed = Signal(str)
                source_changed = Signal(str)
                threshold_changed = Signal(float)

                @property
                def delay(self):
                    """
                    Specifies an additional length of time to delay from the stop trigger to
                    the termination of the generation. The units are seconds.
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.stop.delay

                @delay.setter
                def delay(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.stop.delay = value
                    self.delay_changed.emit(value)

                @property
                def slope(self):
                    """
                    Specifies the slope of the stop trigger.

                    Values for slope:

                    * 'positive'
                    * 'negative'
                    * 'either'
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.stop.slope

                @slope.setter
                def slope(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.stop.slope = value
                    self.slope_changed.emit(value)

                @property
                def source(self):
                    """
                    Specifies the source of the stop trigger.
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.stop.source

                @source.setter
                def source(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.stop.source = value
                    self.source_changed.emit(value)

                @property
                def threshold(self):
                    """
                    Specifies the voltage threshold for the stop trigger. The units are volts.
                    """
                    return self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.stop.threshold

                @threshold.setter
                def threshold(self, value):
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.stop.threshold = value
                    self.threshold_changed.emit(value)

                def configure(self, source, slope):
                    """
                    This function configures the stop trigger properties.
                    """
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.stop.configure(source, slope)

    class trigger:
        class stop(QObject,
                   fgen_ivi_interface.StopTriggerExtensionInterface.trigger.stop,
                   metaclass=QtInterfaceMetaclass):
            def send_software_trigger(self):
                """
                This function sends a software-generated stop trigger to the instrument.
                """
                self.root.driver.trigger.stop.send_software_trigger()


class HoldTriggerExtension(fgen_ivi_interface.HoldTriggerExtensionInterface):
    """
    Extension IVI methods for function generators that support hold triggering

    The Extension Group supports function generators capable of configuring a hold trigger. A hold trigger pauses
    generation. From the paused state, a resume trigger resumes generation; a stop trigger terminates generation;
    start trigger behavior is vendor defined.

    Setting the hold Trigger Source attribute to a value other than None enables the hold trigger. To
    disable the hold trigger, set the Hold Trigger Source to None.
    """
    class outputs:
        class trigger:
            class hold(QObject,
                       fgen_ivi_interface.HoldTriggerExtensionInterface.outputs.trigger.hold,
                       metaclass=QtInterfaceMetaclass):
                delay_changed = Signal(float)
                slope_changed = Signal(str)
                source_changed = Signal(str)
                threshold_changed = Signal(float)

                @property
                def delay(self):
                    """
                    Specifies an additional length of time to delay from the hold trigger to
                    the pause of the generation. The units are seconds.
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.hold.delay

                @delay.setter
                def delay(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.hold.delay = value
                    self.delay_changed.emit(value)

                @property
                def slope(self):
                    """
                    Specifies the slope of the hold trigger.

                    Values for slope:

                    * 'positive'
                    * 'negative'
                    * 'either'
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.hold.slope

                @slope.setter
                def slope(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.hold.slope = value
                    self.slope_changed.emit(value)

                @property
                def source(self):
                    """
                    Specifies the source of the hold trigger.
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.hold.source

                @source.setter
                def source(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.hold.source = value
                    self.source_changed.emit(value)

                @property
                @abc.abstractmethod
                def threshold(self):
                    """
                    Specifies the voltage threshold for the hold trigger. The units are volts.
                    """
                    return self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.hold.threshold

                @threshold.setter
                def threshold(self, value):
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.hold.threshold = value
                    self.threshold_changed.emit(value)

                def configure(self, source, slope):
                    """
                    This function configures the hold trigger properties.
                    """
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.hold.configure(source, slope)

    class trigger:
        class hold(QObject,
                   fgen_ivi_interface.HoldTriggerExtensionInterface.trigger.hold,
                   metaclass=QtInterfaceMetaclass):
            def send_software_trigger(self):
                """
                This function sends a software-generated hold trigger to the instrument.
                """
                self.root.driver.trigger.hold.send_software_trigger()


class ResumeTriggerExtension(fgen_ivi_interface.ResumeTriggerExtensionInterface):
    """
    Extension IVI methods for function generators that support resume triggering

    The Extension Group supports function generators capable of configuring a resume trigger. A resume trigger resumes
    generation after it has been paused by a hold trigger, starting with the next point.
    Setting the Resume Trigger Source attribute to a value other than None enables the resume trigger.
    To disable the resume trigger, set the Resume Trigger Source to None.
    """
    class outputs:
        class trigger:
            class resume(QObject,
                         fgen_ivi_interface.ResumeTriggerExtensionInterface.outputs.trigger.resume,
                         metaclass=QtInterfaceMetaclass):
                delay_changed = Signal(float)
                slope_changed = Signal(str)
                source_changed = Signal(str)
                threshold_changed = Signal(float)

                @property
                def delay(self):
                    """
                    Specifies an additional length of time to delay from the resume trigger to
                    the resumption of the generation. The units are seconds.
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.resume.delay

                @delay.setter
                def delay(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.resume.delay = value
                    self.delay_changed.emit(value)

                @property
                def slope(self):
                    """
                    Specifies the slope of the resume trigger.

                    Values for slope:

                    * 'positive'
                    * 'negative'
                    * 'either'
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.resume.slope

                @slope.setter
                def slope(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.resume.slope = value
                    self.slope_changed.emit(value)

                @property
                def source(self):
                    """
                    Specifies the source of the resume trigger.
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.resume.source

                @source.setter
                def source(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.resume.source = value
                    self.source_changed.emit(value)

                @property
                def threshold(self):
                    """
                    Specifies the voltage threshold for the resume trigger. The units are
                    volts.
                    """
                    return self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.resume.threshold

                @threshold.setter
                def threshold(self, value):
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.resume.threshold = value
                    self.threshold_changed.emit(value)

                def configure(self, source, slope):
                    """
                    This function configures the resume trigger properties.
                    """
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.resume.configure(source, slope)

    class trigger:
        class resume(QObject,
                     fgen_ivi_interface.ResumeTriggerExtensionInterface.trigger.resume,
                     metaclass=QtInterfaceMetaclass):
            def send_software_trigger(self):
                """
                This function sends a software-generated resume trigger to the instrument.
                """
                self.root.driver.trigger.resume.send_software_trigger()


class AdvanceTriggerExtension(fgen_ivi_interface.AdvanceTriggerExtensionInterface):
    """
    Extension IVI methods for function generators that support advance triggering

    The Extension Group supports function generators capable of configuring
    an advance trigger. An advance trigger advances generation to the end of the current waveform,
    where generation proceeds according to the current configuration.
    Setting the Advance Trigger Source attribute to a value other than None enables the advance
    trigger. To disable the advance trigger, set the Advance Trigger Source to None.
    """
    class outputs:
        class trigger:
            @Namespace
            class advance(QObject,
                          fgen_ivi_interface.AdvanceTriggerExtensionInterface.outputs.trigger.advance,
                          metaclass=QtInterfaceMetaclass):
                delay_changed = Signal(float)
                slope_changed = Signal(str)
                source_changed = Signal(str)
                threshold_changed = Signal(float)

                @property
                def delay(self):
                    """
                    Specifies an additional length of time to delay from the advance trigger
                    to the advancing to the end of the current waveform. Units are seconds.
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.advance.delay

                @delay.setter
                def delay(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.advance.delay = value
                    self.delay_changed.emit(value)

                @property
                def slope(self):
                    """
                    Specifies the slope of the advance trigger.

                    Values for slope:

                    * 'positive'
                    * 'negative'
                    * 'either'
                    """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.advance.slope

                @slope.setter
                def slope(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.advance.slope = value
                    self.slope_changed.emit(value)

                @property
                def source(self):
                    """ Specifies the source of the advance trigger. """
                    return self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.advance.source

                @source.setter
                def source(self, value):
                    self.root.driver.outputs[self.parent_namespace.parent_namespace.index].trigger.advance.source = value
                    self.source_changed.emit(value)

                @property
                def threshold(self):
                    """ Specifies the voltage threshold for the advance trigger. The units are volts. """
                    return self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.advance.threshold

                @threshold.setter
                def threshold(self, value):
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.advance.threshold = value
                    self.threshold_changed.emit(value)

                def configure(self, source, slope):
                    """ This function configures the advance trigger properties. """
                    self.root.driver.outputs[
                        self.parent_namespace.parent_namespace.index].trigger.advance.configure(source, slope)

    class trigger:
        @Namespace
        class advance(QObject,
                      fgen_ivi_interface.AdvanceTriggerExtensionInterface.trigger.advance,
                      metaclass=QtInterfaceMetaclass):
            def send_software_trigger(self):
                """ This function sends a software-generated advance trigger to the instrument. """
                self.root.driver.trigger.advance.send_software_trigger()


class InternalTriggerExtension(fgen_ivi_interface.InternalTriggerExtensionInterface):
    """
    Extension IVI methods for function generators that support internal triggering

    The Extension Group supports function generators that can generate output
    based on an internally generated trigger signal. The user can configure the rate at which internal
    triggers are generated.
    This extension affects instrument behavior when the Trigger Source attribute is set to Internal
    Trigger.
    """
    class trigger(fgen_ivi_interface.InternalTriggerExtensionInterface.trigger):
        internal_rate_changed = Signal(float)

        @property
        def internal_rate(self):
            """
            Specifies the rate at which the function generator's internal trigger
            source produces a trigger, in triggers per second.
            """
            return self.root.driver.trigger.internal_rate

        @internal_rate.setter
        def internal_rate(self, value):
            self.root.driver.trigger.internal_rate = value
            self.internal_rate_changed.emit(value)


class SoftwareTriggerExtension(fgen_ivi_interface.SoftwareTriggerExtensionInterface):
    """
    Extension IVI methods for function generators that support software triggering

    The Extension Group supports function generators that can generate
    output based on a software trigger signal. The user can send a software trigger to cause signal
    output to occur.
    This extension affects instrument behavior when the Trigger Source attribute is set to Software
    Trigger
    """
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
        self.root.driver.send_software_trigger()


class BurstExtension(fgen_ivi_interface.BurstExtensionInterface):
    """
    Extension IVI methods for function generators that support triggered burst output.

    The IviFgenBurst Extension Group supports function generators capable of generating a discrete number of waveform
    cycles based on a trigger. The trigger is configured with the IviFgenTrigger or IviFgenStartTrigger extension
    group. The user can specify the number of waveform cycles to generate when a trigger event occurs.
    For standard and arbitrary waveforms, a cycle is one period of the waveform. For arbitrary sequences, a cycle is
    one complete progression through the generation of all iterations of all waveforms in the sequence.
    This extension affects instrument behavior when the Operation Mode attribute is set to Operate Burst.
    """
    class outputs(fgen_ivi_interface.BurstExtensionInterface.outputs):
        burst_count_changed = Signal(int)

        @property
        def burst_count(self):
            """
            Specifies the number of waveform cycles that the function generator
            produces after it receives a trigger.
            """
            return self.root.driver.outputs[self.parent_namespace.index].burst_count

        @burst_count.setter
        def burst_count(self, value):
            self.root.driver.outputs[self.parent_namespace.index].burst_count = value
            self.burst_count_changed.emit(value)


class ModulateAMExtension(fgen_ivi_interface.ModulateAMExtensionInterface):
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
    """
    class outputs:
        @Namespace
        class am(QObject,
                 fgen_ivi_interface.ModulateAMExtensionInterface.outputs.am,
                 metaclass=QtInterfaceMetaclass):
            enabled_changed = Signal(bool)
            source_changed = Signal(str)

            @property
            def enabled(self):
                """
                Specifies whether the function generator applies amplitude modulation to
                the signal that the function generator produces with the IviFgenStdFunc,
                IviFgenArbWfm, or IviFgenArbSeq capability groups. If set to True, the
                function generator applies amplitude modulation to the output signal. If
                set to False, the function generator does not apply amplitude modulation
                to the output signal.
                """
                return self.root.driver.outputs[self.parent_namespace.index].am.enabled

            @enabled.setter
            def enabled(self, value):
                self.root.driver.outputs[self.parent_namespace.index].am.enabled = value
                self.enabled_changed.emit(value)

            @property
            def source(self):
                """
                Specifies the source of the signal that the function generator uses as the
                modulating waveform.

                This attribute affects instrument behavior only when the AM Enabled
                attribute is set to True.
                """
                return self.root.driver.outputs[self.parent_namespace.index].am.source

            @source.setter
            def source(self, value):
                self.root.driver.outputs[self.parent_namespace.index].am.source = value
                self.source_changed.emit(value)

    class am(QObject,
             fgen_ivi_interface.ModulateAMExtensionInterface.am,
             metaclass=QtInterfaceMetaclass):
        internal_depth_changed = Signal(float)
        internal_frequency_changed = Signal(float)
        internal_waveform_changed = Signal(str)

        @property
        def internal_depth(self):
            """
            Specifies the extent of modulation the function generator applies to the
            carrier waveform when the AM Source attribute is set to AM Internal. The
            unit is percentage.

            This attribute affects the behavior of the instrument only when the AM
            ource attribute is set to AM Internal.
            """
            return self.root.driver.am.internal_depth

        @internal_depth.setter
        def internal_depth(self,value):
            self.root.driver.am.internal_depth = value
            self.internal_depth_changed.emit(value)

        @property
        @abc.abstractmethod
        def internal_frequency(self):
            """
            Specifies the frequency of the internal modulating waveform source. The
            units are Hertz.

            This attribute affects the behavior of the instrument only when the AM
            ource attribute is set to AM Internal.
            """
            return self.root.driver.am.internal_frequency

        @internal_frequency.setter
        def internal_frequency(self, value):
            self.root.driver.am.internal_frequency = value
            self.internal_frequency_changed.emit(value)

        @property
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
            return self.root.driver.am.internal_waveform

        @internal_waveform.setter
        def internal_waveform(self, value):
            self.root.driver.am.internal_waveform = value
            self.internal_waveform_changed.emit(value)

        def configure_internal(self, modulation_depth, waveform, frequency):
            """
            Configures the attributes that control the function generator's internal
            amplitude modulating waveform source. These attributes are the modulation
            depth, waveform, and frequency.
            """
            self.root.driver.am.configure_internal(modulation_depth, waveform, frequency)


class ModulateFMExtension(fgen_ivi_interface.ModulateFMExtensionInterface):
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
    """
    class outputs:
        @Namespace
        class fm(QObject,
                 fgen_ivi_interface.ModulateFMExtensionInterface.outputs.fm,
                 metaclass=QtInterfaceMetaclass):
            enabled_changed = Signal(bool)
            source_changed = Signal(str)

            @property
            def enabled(self):
                """
                Specifies whether the function generator applies amplitude modulation to
                the carrier waveform. If set to True, the function generator applies
                frequency modulation to the output signal. If set to False, the function
                generator does not apply frequency modulation to the output signal.
                """
                return self.root.driver.outputs[self.parent_namespace.index].fm.enabled

            @enabled.setter
            def enabled(self, value):
                self.root.driver.outputs[self.parent_namespace.index].fm.enabled = value
                self.enabled_changed.emit(value)

            @property
            def source(self):
                """
                Specifies the source of the signal that the function generator uses as the
                modulating waveform.

                This attribute affects instrument behavior only when the FM Enabled
                attribute is set to True.
                """
                return self.root.driver.outputs[self.parent_namespace.index].fm.source

            @source.setter
            def source(self, value):
                self.root.driver.outputs[self.parent_namespace.index].fm.source = value
                self.source_changed.emit(value)

    class fm(QObject,
             fgen_ivi_interface.ModulateFMExtensionInterface.fm,
             metaclass=QtInterfaceMetaclass):
        internal_deviation_changed = Signal(float)
        internal_frequency_changed = Signal(float)
        internal_waveform_changed = Signal(str)

        @property
        def internal_deviation(self):
            """
            Specifies the maximum frequency deviation, in Hertz, that the function
            generator applies to the carrier waveform when the FM Source attribute is
            set to FM Internal.

            This attribute affects the behavior of the instrument only when the FM
            Source attribute is set to FM Internal.
            """
            return self.root.driver.fm.internal_deviation

        @internal_deviation.setter
        def internal_deviation(self, value):
            self.root.driver.am.internal_deviation = value
            self.internal_deviation_changed.emit(value)

        @property
        def internal_frequency(self):
            """
            Specifies the frequency of the internal modulating waveform source. The
            units are hertz.

            This attribute affects the behavior of the instrument only when the FM
            Source attribute is set to FM Internal.
            """
            return self.root.driver.fm.internal_frequency

        @internal_frequency.setter
        def internal_frequency(self, value):
            self.root.driver.fm.internal_frequency = value
            self.internal_frequency_changed.emit(value)

        @property
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
            return self.root.driver.fm.internal_waveform

        @internal_waveform.setter
        def internal_waveform(self, value):
            self.root.driver.fm.internal_waveform = value
            self.internal_waveform_changed.emit(value)

        @abc.abstractmethod
        def configure_internal(self, deviation, waveform, frequency):
            """
            Configures the attributes that control the function generator's internal frequency
            modulating waveform source. These attributes are the modulation peak deviation, waveform,
            and frequency.

            This attribute affects instrument behavior only when the FM Enabled
            attribute is set to True.
            """
            self.root.driver.fm.configure_internal(deviation, waveform, frequency)


class SampleClockExtension(fgen_ivi_interface.SampleClockExtensionInterface):
    """
    Extension IVI methods for function generators that support external sample clocks

    The IviFgenSampleClock extension group supports arbitrary waveform generators with the ability
    to use (or provide) an external sample clock. Note that when using an external sample clock,
    the Arbitrary Sample Rate attribute must be set to the corresponding frequency of the external
    sample clock.
    """
    class sample_clock(QObject,
                       fgen_ivi_interface.SampleClockExtensionInterface.sample_clock,
                       metaclass=QtInterfaceMetaclass):
        source_changed = Signal(str)
        output_enabled_changed = Signal(bool)

        @property
        def source(self):
            """
            Specifies the clock used for the waveform generation. Note that when using
            an external sample clock, the Arbitrary Sample Rate attribute must be set
            to the corresponding frequency of the external sample clock.
            """
            return self.root.driver.sample_clock.source

        @source.setter
        def source(self, value):
            self.root.driver.sample_clock.source = value
            self.source_changed.emit(value)

        @property
        @abc.abstractmethod
        def output_enabled(self):
            """
            Specifies whether or not the sample clock appears at the sample clock output of the
            generator.
            """
            return self.root.driver.sample_clock.output_enabled

        @output_enabled.setter
        def output_enabled(self, value):
            self.root.driver.sample_clock.output_enabled = value
            self.output_enabled_changed.emit(value)


class TerminalConfigurationExtension(fgen_ivi_interface.TerminalConfigurationExtensionInterface):
    """
    Extension IVI methods for function generators that support single ended or differential
    output selection.
    """
    class outputs(fgen_ivi_interface.TerminalConfigurationExtensionInterface.outputs):
        terminal_configuration_changed = Signal(str)

        @property
        def terminal_configuration(self):
            """
            Determines whether the generator will run in single-ended or differential
            mode, and whether the output gain and offset values will be analyzed
            based on single-ended or differential operation.

            Values for terminal_configuration:

            * 'single_ended'
            * 'differential'
            """
            return self.root.driver.outputs[self.parent_namespace.index].terminal_configuration

        @terminal_configuration.setter
        def terminal_configuration(self, value):
            self.root.driver.outputs[self.parent_namespace.index].terminal_configuration = value
            self.terminal_configuration_changed.emit(value)


class ArbChannelWfmExtension(fgen_ivi_interface.ArbChannelWfmExtensionInterface):
    """
    Extension IVI methods for function generators that support user-defined arbitrary waveform
    generation

    The IviFgenArbChannelWfm Extension Group supports single channel and multichannel function
    generators capable of producing user-defined arbitrary waveforms for specific output channels.
    The IviFgenArbChannelWfm extension group includes functions for creating, configuring, and
    generating arbitrary waveforms.
    """
    class outputs:
        class arbitrary:
            class waveform(fgen_ivi_interface.ArbChannelWfmExtensionInterface.outputs.arbitrary.waveform):
                def create_waveform(self, data):
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
                    return self.root.driver.outputs[self.parent_namespace.index].arbitrary.create_waveform(data)

    class arbitrary:
        class waveform(fgen_ivi_interface.ArbChannelWfmExtensionInterface.arbitrary.waveform):
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
                return self.root.driver.arbitrary.waveform.create_channel_waveform(channel_names, waveforms)


class ArbWfmBinaryExtension(fgen_ivi_interface.ArbWfmBinaryExtensionInterface):
    """
    Extension IVI methods for function generators that support user-defined arbitrary binary
    waveform generation

    The IviFgenArbWfmBinary Extension Group supports multichannel function generators capable of
    producing user-defined arbitrary waveforms that can be specified in binary format. The
    IviFgenArbWfmBinary extension group includes functions for creating, configuring, and generating
    arbitrary waveforms.
    """
    class outputs:
        class arbitrary:
            class waveform(fgen_ivi_interface.ArbWfmBinaryExtensionInterface.outputs.arbitrary.waveform):
                def create_waveform_int16(self, waveform):
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

                    If the function generator cannot store any more arbitrary waveforms, this
                    function returns the error No Waveforms Available.
                    """
                    return self.root.driver.outputs[
                        self.parent_namespace.index].arbitrary.waveform.create_channel_waveform_int16(waveform)

                def create_waveform_int32(self, waveform):
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

                    If the function generator cannot store any more arbitrary waveforms, this
                    function returns the error No Waveforms Available.
                    """
                    return self.root.driver.outputs[
                        self.parent_namespace.index].arbitrary.waveform.create_channel_waveform_int32(waveform)

    class arbitrary(fgen_ivi_interface.ArbWfmBinaryExtensionInterface.arbitrary):
        @property
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
            return self.root.driver.arbitrary.binary_alignment

        @property
        def sample_bit_resolution(self):
            """
            Returns the number of significant bits that the generator supports in an
            arbitrary waveform. Together with the binary alignment, this allows the
            user to know the range and resolution of the integers in the waveform.
            """
            return self.root.driver.arbitrary.sample_bit_resolution

        class waveform(fgen_ivi_interface.ArbWfmBinaryExtensionInterface.arbitrary.waveform):
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
                return self.root.driver.arbitrary.waveform.create_channel_waveform_int16(channel_names, waveforms)

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
                return self.root.driver.arbitrary.waveform.create_channel_waveform_int32(channel_names, waveforms)


class DataMarkerExtension(fgen_ivi_interface.DataMarkerExtensionInterface):
    """
    Extension IVI methods for function generators that support output of particular waveform data
    bits as markers

    The IviFgenDataMarker Extension Group supports arbitrary waveform generators that can output
    particular bits of waveform data as a marker output. The user can choose which bit (the 2nd bit
    for example) gets output, where the output goes, and various analog characteristics of the
    marker output. Data markers are repeated capabilities to allow the user to output multiple bits
    to different ouputs simultaneously. The user can also use the DataMask property to ensure that
    the data marker does not get output with the main waveform output.

    Setting the Data Marker Destination attribute to a value other than None enables the data
    marker. To disable the data marker, set the Data Marker Destination to None.
    """
    class data_markers(fgen_ivi_interface.DataMarkerExtensionInterface.data_markers):
        amplitude_changed = Signal(float)
        bit_position_changed = Signal(int)
        delay_changed = Signal(float)
        destination_changed = Signal(str)
        polarity_changed = Signal(str)
        source_channel_changed = Signal(str)

        @property
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
            return self.root.driver.data_markers[self.parent_namespace.index].name

        @property
        def amplitude(self):
            """
            Specifies the amplitude of the data marker output. The units are volts.
            """
            return self.root.driver.data_markers[self.parent_namespace.index].amplitude

        @amplitude.setter
        def amplitude(self, value):
            self.root.driver.data_markers[self.parent_namespace.index].amplitude = value
            self.amplitude_changed.emit(value)

        @property
        def bit_position(self):
            """
            Specifies the bit position of the binary representation of the waveform
            data that will be output as a data marker. A value of 0 indicates the
            least significant bit.
            """
            return self.root.driver.data_markers[self.parent_namespace.index].bit_position

        @bit_position.setter
        def bit_position(self, value):
            self.root.driver.data_markers[self.parent_namespace.index].bit_position = value
            self.bit_position_changed.emit(value)

        @property
        def delay(self):
            """
            Specifies the amount of delay applied to the data marker output with
            respect to the analog data output. A value of zero indicates the marker is
            aligned with the analog data output.  The units are seconds.
            """
            return self.root.driver.data_markers[self.parent_namespace.index].delay

        @delay.setter
        def delay(self, value):
            self.root.driver.data_markers[self.parent_namespace.index].delay = value
            self.delay_changed.emit(value)

        @property
        def destination(self):
            """
            Specifies the destination terminal for the data marker output.
            """
            return self.root.driver.data_markers[self.parent_namespace.index].destination

        @destination.setter
        def destination(self, value):
            self.root.driver.data_markers[self.parent_namespace.index].destination = value
            self.destination_changed.emit(value)

        @property
        def polarity(self):
            """
            Specifies the polarity of the data marker output.

            Values for polarity:

            * 'active_high'
            * 'active_low'
            """
            return self.root.driver.data_markers[self.parent_namespace.index].polarity

        @polarity.setter
        def polarity(self, value):
            self.root.driver.data_markers[self.parent_namespace.index].polarity = value
            self.polarity_changed.emit(value)

        @property
        def source_channel(self):
            """
            Specifies the channel whose data bit will be output as a marker.
            """
            return self.root.driver.data_markers[self.parent_namespace.index].source_channel

        @source_channel.setter
        def source_channel(self, value):
            self.root.driver.data_markers[self.parent_namespace.index].source_channel = value
            self.source_channel_changed.emit(value)

        def configure(self, source_channel, bit_position, destination):
            """
            Configures some of the common data marker attributes: source channel, bit position and
            destination.
            """
            self.root.driver.data_markers[self.parent_namespace.index].configure(source_channel,
                                                                                 bit_position,
                                                                                 destination)

        def clear(self):
            """
            Disables all of the data markers by setting their Data Marker Destination
            attribute to None.
            """
            self.root.driver.data_markers[self.parent_namespace.index].clear()


class ArbDataMaskExtension(fgen_ivi_interface.ArbDataMaskExtensionInterface):
    """
    Extension IVI methods for function generators that support masking of waveform data bits

    The IviFgenArbDataMask extension group supports arbitrary waveform generators with the ability
    to mask out bits of the output data.
    """
    class arbitrary(fgen_ivi_interface.ArbDataMaskExtensionInterface.arbitrary):
        data_mask_changed = Signal(int)

        @property
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
            return self.root.driver.arbitrary.data_mask

        @data_mask.setter
        def data_mask(self, value):
            self.root.driver.arbitrary.data_mask = value
            self.data_mask_changed.emit(value)


class SparseMarkerExtension(fgen_ivi_interface.SparseMarkerExtensionInterface):
    """
    Extension IVI methods for function generators that support output of markers associated with
    output data samples.

    The IviFgenSparseMarker Extension Group supports arbitrary waveform generators that can output
    signals, known as markers, associated with specified samples in the output data. Unlike data
    markers, sparse markers are not stored as part of the waveform data, but rather provided as a
    list of particular samples of the waveform on which the marker should be output. The user can
    choose which waveform and sample number the output is associated with, where the output goes,
    and various analog characteristics of the marker output. Sparse markers are repeated
    capabilities to allow the user to specify multiple markers to different outputs simultaneously.

    Setting the Sparse Marker Destination attribute to a value other than None enables the sparse
    marker. To disable the sparse marker, set the Sparse Marker Destination to None.
    """
    class sparse_markers(QObject,
                         fgen_ivi_interface.SparseMarkerExtensionInterface.sparse_markers,
                         metaclass=QtInterfaceMetaclass):
        amplitude_changed = Signal(float)
        bit_position_changed = Signal(int)
        delay_changed = Signal(float)
        destination_changed = Signal(str)
        polarity_changed = Signal(str)
        waveform_handle_changed = Signal(str)
        indexes_changed = Signal()

        @property
        def name(self):
            """
            This attribute returns the repeated capability identifier defined by
            specific driver for the sparse marker that corresponds to the index that
            the user specifies. If the driver defines a qualified Sparse Marker name,
            this property returns the qualified name.
            """
            return self.root.driver.sparse_markers[self.parent_namespace.index].name

        @property
        def amplitude(self):
            """
            Specifies the amplitude of the sparse marker output. The units are volts.
            """
            return self.root.driver.sparse_markers[self.parent_namespace.index].amplitude

        @amplitude.setter
        def amplitude(self, value):
            self.root.driver.sparse_markers[self.parent_namespace.index].amplitude = value
            self.amplitude_changed.emit(value)

        @property
        def delay(self):
            """
            Specifies the amount of delay applied to the sparse marker output with
            respect to the analog data output. A value of zero indicates the marker is
            aligned with the analog data output. The units are seconds.
            """
            return self.root.driver.sparse_markers[self.parent_namespace.index].delay

        @delay.setter
        def delay(self, value):
            self.root.driver.sparse_markers[self.parent_namespace.index].delay = value
            self.delay_changed.emit(value)

        @property
        def destination(self):
            """
            Specifies the destination terminal for the sparse marker output.
            """
            return self.root.driver.sparse_markers[self.parent_namespace.index].destination

        @destination.setter
        def destination(self, value):
            self.root.driver.sparse_markers[self.parent_namespace.index].destination = value
            self.destination_changed.emit(value)

        @property
        def polarity(self):
            """
            Specifies the polarity of the sparse marker output.

            Values for polarity:

            * 'active_high'
            * 'active_low'
            """
            return self.root.driver.sparse_markers[self.parent_namespace.index].polarity

        @polarity.setter
        def polarity(self, value):
            self.root.driver.sparse_markers[self.parent_namespace.index].polarity = value
            self.polarity_changed.emit(value)

        @property
        def waveform_handle(self):
            """
            Specifies the waveform whose indexes the sparse marker refers to.
            """
            return self.root.driver.sparse_markers[self.parent_namespace.index].waveform_handle

        @waveform_handle.setter
        def waveform_handle(self, value):
            self.root.driver.sparse_markers[self.parent_namespace.index].waveform_handle = value
            self.waveform_handle_changed.emit(value)

        def configure(self, waveform_handle, indexes, destination):
            """
            Configures some of the common sparse marker attributes.
            """
            self.root.driver.sparse_markers[self.parent_namespace.index].configure(waveform_handle,
                                                                                   indexes,
                                                                                   destination)

        def get_indexes(self):
            """
            Gets the coerced indexes associated with the sparse marker. These indexes
            are specified by either the Configure SparseMarker function or the Set
            Sparse Marker Indexes function.
            """
            return self.root.driver.sparse_markers[self.parent_namespace.index].get_indexes()

        def set_indexes(self, indexes):
            """
            Sets the indexes associated with the sparse marker. These indexes may be
            coerced by the driver. Use the Get Sparse Marker Indexes function to find
            the coerced values.
            """
            self.root.driver.sparse_markers[self.parent_namespace.index].set_indexes(indexes)
            self.indexes_changed.emit()

        def clear(self):
            """
            Disables all of the sparse markers by setting their Sparse Marker
            Destination attribute to None.
            """
            self.root.driver.sparse_markers[self.parent_namespace.index].clear()


class ArbSeqDepthExtension(fgen_ivi_interface.ArbSeqDepthExtensionInterface):
    """
    Extension IVI methods for function generators that support producing sequences of sequences
    of waveforms.

    The IviFgenArbSeqDepth extension group supports arbitrary waveform generators supporting
    IviFgenArbSeq and that are capable of producing sequences of sequences of arbitrary waveforms.
    """
    class arbitrary:
        class sequence(fgen_ivi_interface.ArbSeqDepthExtensionInterface.arbitrary.sequence):
            @property
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
                return self.root.driver.arbitrary.sequence.depth_max


class PythonIviFGen(PythonIviBase, _FGen, fgen_ivi_interface.FGenIviInterface):
    """
    Module for accessing arbitrary waveform / function generators via PythonIVI library.

    Config options:
    - driver : str module.class name of driver within the python IVI library
                   e.g. 'ivi.tektronix.tektronixAWG5000.tektronixAWG5002c'
    - uri : str unique remote identifier used to connect to instrument.
                e.g. 'TCPIP0::192.168.1.1::INSTR'
    """
    def __getattribute__(self, name):
        """
        this enables getting data from dynamic descriptors
        :param name: name of attribute
        :return: the attribute
        """
        value = object.__getattribute__(self, name)
        if hasattr(value, '__get__'):
            value = value.__get__(self, self.__class__)
        return value

    def __setattr__(self, name, value):
        """
        this enables settings data from dyamic descriptors
        :param name: name of attribute
        :param value: value
        :return:
        """
        try:
            obj = object.__getattribute__(self, name)
        except AttributeError:
            pass
        else:
            if hasattr(obj, '__set__'):
                return obj.__set__(self, value)
        return object.__setattr__(self, name, value)

    def on_activate(self):
        super().on_activate()

        # find all base classes of driver
        driver_capabilities = inspect.getmro(type(self.driver))

        # dynamic class generator
        class IviOutputArbitraryWaveformMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.fgen.ArbChannelWfm in driver_capabilities:
                    bases += (ArbChannelWfmExtension.outputs.arbitrary,)
                if ivi.fgen.ArbWfmBinary in driver_capabilities:
                    bases += (ArbWfmBinaryExtension, )
                return super().__new__(mcs, name, bases, attrs)

        class IviOutputArbitraryWaveform(QObject, metaclass=IviOutputArbitraryWaveformMetaclass):
            pass

        class IviOutputArbitraryMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.fgen.ArbWfm in driver_capabilities:
                    bases += (ArbWfmExtension.outputs.arbitrary, )
                if ivi.fgen.ArbFrequency in driver_capabilities:
                    bases += (ArbFrequencyExtension.outputs.arbitrary, )
                if ivi.fgen.ArbSeq in driver_capabilities:
                    bases += (ArbSeqExtension.outputs.arbitrary, )
                return super().__new__(mcs, name, bases, attrs)

        class IviOutputArbitrary(QObject, metaclass=IviOutputArbitraryMetaclass):
            waveform = Namespace(IviOutputArbitraryWaveform)

        class IviOutputTriggerMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.fgen.StartTrigger in driver_capabilities:
                    bases += (StartTriggerExtension.outputs.trigger, )
                if ivi.fgen.StopTrigger in driver_capabilities:
                    bases += (StopTriggerExtension.outputs.trigger, )
                if ivi.fgen.HoldTrigger in driver_capabilities:
                    bases += (HoldTriggerExtension.outputs.trigger, )
                if ivi.fgen.ResumeTrigger in driver_capabilities:
                    bases += (ResumeTriggerExtension.outputs.trigger, )
                if ivi.fgen.AdvanceTrigger in driver_capabilities:
                    bases += (AdvanceTriggerExtension.outputs.trigger, )
                return super().__new__(mcs, name, bases, attrs)

        class IviOutputTrigger(QObject, metaclass=IviOutputTriggerMetaclass):
            pass

        class IviOutputMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                bases = bases + (_FGen.outputs, )
                if ivi.fgen.StdFunc in driver_capabilities:
                    bases += (StdFuncExtension.outputs, )
                if ivi.fgen.Burst in driver_capabilities:
                    bases += (BurstExtension.outputs, )
                if ivi.fgen.ModulateAM in driver_capabilities:
                    bases += (ModulateAMExtension.outputs, )
                if ivi.fgen.ModulateFM in driver_capabilities:
                    bases += (ModulateFMExtension.outputs, )
                if ivi.fgen.TerminalConfiguration in driver_capabilities:
                    bases += (TerminalConfigurationExtension.outputs, )
                return super().__new__(mcs, name, bases, attrs)

        class IviOutput(QObject, metaclass=IviOutputMetaclass):
            arbitrary = Namespace(IviOutputArbitrary)
            trigger = Namespace(IviOutputTrigger)

        self.outputs = Namespace.repeat(self.driver._output_count)(IviOutput)

        if ivi.fgen.ModulateAM in driver_capabilities:
            self.am = Namespace(ModulateAMExtension.am)
        if ivi.fgen.ModulateFM in driver_capabilities:
            self.fm = Namespace(ModulateFMExtension.fm)
        if ivi.fgen.SampleClock in driver_capabilities:
            self.sample_clock = Namespace(SampleClockExtension.sample_clock)


        class IviArbitraryWaveformMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.fgen.ArbChannelWfm in driver_capabilities:
                    bases += (ArbChannelWfmExtension.arbitrary.waveform, )
                if ivi.fgen.ArbWfmBinary in driver_capabilities:
                    bases += (ArbWfmBinaryExtension.arbitrary.waveform)
                return super().__new__(mcs, name, bases, attrs)

        class IviArbitraryWaveform(QObject, metaclass=IviArbitraryWaveformMetaclass):
            pass

        class IviArbitrarySequenceMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.fgen.ArbSeqDepth in driver_capabilities:
                    bases += (ArbSeqDepthExtension.arbitrary.sequence, )
                return super().__new__(mcs, name, bases, attrs)

        class IviArbitrarySequence(QObject, metaclass=IviArbitrarySequenceMetaclass):
            pass

        class IviArbitraryMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.fgen.ArbDataMask in driver_capabilities:
                    bases += (ArbDataMaskExtension.arbitrary, )
                if ivi.fgen.ArbWfmBinary in driver_capabilities:
                    bases += (ArbWfmBinaryExtension.arbitrary, )
                return super().__new__(mcs, name, bases, attrs)

        class IviArbitrary(QObject, metaclass=IviArbitraryMetaclass):
            waveform = Namespace(IviArbitraryWaveform)
            sequence = Namespace(IviArbitrarySequence)

        self.arbitrary = Namespace(IviArbitrary)

        class IviTriggerMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.fgen.StartTrigger in driver_capabilities:
                    bases += (StartTriggerExtension.trigger, )
                if ivi.fgen.StopTrigger in driver_capabilities:
                    bases += (StopTriggerExtension.trigger, )
                if ivi.fgen.HoldTrigger in driver_capabilities:
                    bases += (HoldTriggerExtension.trigger, )
                if ivi.fgen.ResumeTrigger in driver_capabilities:
                    bases += (ResumeTriggerExtension.trigger, )
                if ivi.fgen.AdvanceTrigger in driver_capabilities:
                    bases += (AdvanceTriggerExtension.trigger, )
                if ivi.fgen.InternalTrigger in driver_capabilities:
                    bases += (InternalTriggerExtension.trigger, )
                return super().__new__(mcs, name, bases, attrs)

        class IviTrigger(QObject, metaclass=IviTriggerMetaclass):
            pass

        self.trigger = Namespace(IviTrigger)

        if ivi.fgen.DataMarker in driver_capabilities:
            self.data_markers = Namespace.repeat(self.driver._data_marker_count)(DataMarkerExtension.data_markers)
        if ivi.fgen.SparseMarker in driver_capabilities:
            self.sparse_markers = Namespace.repeat(self.driver._sparse_marker_count)(SparseMarkerExtension.sparse_markers)

