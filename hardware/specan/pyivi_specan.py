# -*- coding: utf-8 -*-
"""
This file contains the implementation of the pythonIvi interface for scopes.

The main class is ::PyIviScope::

Example configuration

hardware:
    n9000a:
        module.Class: 'scope.pyivi_specan.PyIviSpecan'
        uri: 'TCPIP::192.168.1.1::INSTR'


Optional parameter:
        flavour: either 'IVI-COM' or 'IVI-C', two of the interfaces IVI supports. Default: IVI-COM.
        simulate: boolean

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


from interface.ivi import specan_interface as specan_ivi_interface
from .._pyivi_base import PyIviBase
from .._pyivi_base import QtInterfaceMetaclass
from .._ivi_core import Namespace

import abc
from qtpy.QtCore import QObject
from qtpy.QtCore import Signal
from comtypes.safearray import safearray_as_ndarray
import numpy


class _Specan(specan_ivi_interface.SpecAnIviInterface):
    """

    """
    @Namespace
    class level(QObject, specan_ivi_interface.SpecAnIviInterface.level, metaclass=QtInterfaceMetaclass):
        amplitude_units_changed = Signal(specan_ivi_interface.AmplitudeUnits)
        attenuation_changed = Signal(float)
        attenuation_auto_changed = Signal(bool)
        input_impedance_changed = Signal(int)
        reference_changed = Signal(float)
        reference_offset_changed = Signal(float)

        @property
        def amplitude_units(self):
            """
            Specifies the amplitude units for input, output and display amplitude.
            """
            return specan_ivi_interface.AmplitudeUnits(self.root.driver.level.amplitude_units - 1)

        @amplitude_units.setter
        def amplitude_units(self, value):
            self.root.driver.level.amplitude_units = value.value + 1
            self.amplitude_units_changed.emit(value)

        @property
        def attenuation(self):
            """
            Specifies the input attenuation (in positive dB).
            """
            return self.root.driver.level.attenuation

        @attenuation.setter
        def attenuation(self, value):
            self.root.driver.level.attenuation = value
            self.attenuation_changed.emit(value)

        @property
        def attenuation_auto(self):
            """
            Selects attenuation automatically.

            If set to True, attenuation is automatically selected. If set to False, attenuation is manually selected.
            """
            return self.root.driver.level.attenuation_auto

        @attenuation_auto.setter
        def attenuation_auto(self, value):
            self.root.driver.level.attenuation_auto = value
            self.attenuation_auto_changed.emit(value)

        @property
        def input_impedance(self):
            """
            Specifies the value of input impedance.

            Specifies the value of input impedance, in ohms, expected at the active input port. This is typically
            50 ohms or 75 ohms.
            """
            return self.root.driver.level.input_impedance

        @input_impedance.setter
        def input_impedance(self, value):
            self.root.driver.level.input_impedance = value
            self.input_impedance_changed.emit(value)

        @property
        def reference(self):
            """
            The calibrated vertical position of the captured data used as a reference for amplitude measurements. This
            is typically set to a value slightly higher than the highest expected signal level. The units are
            determined by the Amplitude Units attribute.
            """
            return self.root.driver.level.reference

        @reference.setter
        def reference(self, value):
            self.root.driver.level.reference = value
            self.reference_changed.emit(value)

        @property
        def reference_offset(self):
            """
            Specifies an offset for the Reference Level attribute.

            This value is used to adjust the reference level for external signal gain or loss. A positive value
            corresponds to a gain while a negative number corresponds to a loss. The value is in dB.
            """
            return self.root.driver.level.reference_offset

        @reference_offset.setter
        def reference_offset(self, value):
            self.root.driver.level.reference_offset = value
            self.reference_offset_changed.emit(value)

        def configure(self, amplitude_units, input_impedance, reference_level, reference_level_offset, attenuation):
            """

            :param amplitude_units: Specifies the amplitude units for input, output and display. The driver uses this
                                    value to set the Amplitude Units attribute. See the attribute description for more
                                    details.
            :param input_impedance: Specifies the input impedance. The driver uses this value to set the Input Impedance
                                    attribute. See the attribute description for more details.
            :param reference_level: Specifies the amplitude value of the reference level. The driver uses this value to
                                    set the Reference Level attribute. See the attribute description for more details.
            :param reference_level_offset: Specifies the offset value to the reference level. The driver uses this
                                           value to set the Reference Level Offset attribute. See the attribute
                                           description for more details.
            :param attenuation: either boolean, Enables or disables auto attenuation. The driver uses this value to
                                                set the Attenuation Auto attribute. See the attribute description for
                                                more details.
                                or double, Specifies the attenuation level. The driver uses this value to set the
                                           Attenuation attribute. See the attribute description for more details.
            """
            self.root.driver.level.configure(amplitude_units,
                                             input_impedance,
                                             reference_level,
                                             reference_level_offset,
                                             attenuation)

    @Namespace
    class acquisition(QObject, specan_ivi_interface.SpecAnIviInterface.acquisition, metaclass=QtInterfaceMetaclass):
        detector_type_changed = Signal(specan_ivi_interface.DetectorType)
        detector_type_auto_changed = Signal(bool)
        number_of_sweeps_changed = Signal(int)
        sweep_mode_continuous_changed = Signal(bool)
        vertical_scale_changed = Signal(specan_ivi_interface.VerticalScale)

        @property
        def detector_type(self):
            """
            Specifies the detector type.

            Specifies the detection method used to capture and process the signal. This governs the data acquisition
            for a particular sweep, but does not have any control over how multiple sweeps are processed.
            """
            return specan_ivi_interface.DetectorType(self.root.driver.sc.detector_type - 1)

        @detector_type.setter
        def detector_type(self, value):
            self.root.driver.sc.detector_type = value.value + 1
            self.detector_type_changed.emit(value)

        @property
        def detector_type_auto(self):
            """
            Select detector type automatically.

            If set to True, the detector type is automatically selected. The relationship between Trace Type and
            Detector Type is not defined by the specification when the Detector Type Auto is set to True. If set to
            False, the detector type is manually selected.
            """
            return self.root.driver.acquisition.detector_type_auto

        @detector_type_auto.setter
        def detector_type_auto(self, value):
            self.root.driver.acquisition.detector_type_auto = value
            self.detector_type_auto_changed.emit(value)

        @property
        def number_of_sweeps(self):
            """
            This attribute defines the number of sweeps.

            This attribute value has no effect if the Trace Type attribute is set to the value Clear Write.
            """
            return self.root.driver.sc.number_of_sweeps

        @number_of_sweeps.setter
        def number_of_sweeps(self, value):
            self.root.driver.sc.number_of_sweeps = value
            self.number_of_sweeps_changed.emit(value)

        @property
        def sweep_mode_continuous(self):
            """
            Is the sweep mode continuous?

            If set to True, the sweep mode is continuous If set to False, the sweep mode is not continuous.
            """
            return self.root.driver.acquisition.sweep_mode_continuous

        @sweep_mode_continuous.setter
        def sweep_mode_continuous(self, value):
            self.root.driver.acquisition.sweep_mode_continuous = value
            self.sweep_mode_continuous_changed.emit(value)

        @property
        def vertical_scale(self):
            """
            Specifies the vertical scale of the measurement hardware (use of log amplifiers versus linear amplifiers).
            """
            return specan_ivi_interface.VerticalScale(self.root.driver.acquisition.vertical_scale - 1)

        @vertical_scale.setter
        def vertical_scale(self, value):
            self.root.driver.acquisition.vertical_scale = value.value + 1
            self.vertical_scale_changed.emit(value)

        def configure(self, sweep_mode_continuous, number_of_sweeps, detector_type_auto, detector_type,
                      vertical_scale):
            """
            This function configures the acquisition attributes of the spectrum analyzer.

            :param sweep_mode_continuous: Enables or disables continuous sweeping. The driver uses this value to set the
                                          Sweep Mode Continuous attribute. See the attribute description for more
                                          details.
            :param number_of_sweeps: Specifies the number of sweeps to take. The driver uses this value to set the
                                     Number Of Sweeps attribute. See the attribute description for more details.
            :param detector_type_auto: Enables or Disables the auto detector. The driver uses this value to set the
                                       Detector Type Auto attribute. See the attribute description for more details.
            :param detector_type: Specifies the method of capturing and processing signal data. The driver uses this
                                  value to set the Detector Type attribute. See the attribute description for more
                                  details.
            :param vertical_scale: Specifies the vertical scale. The driver uses this value to set the Vertical Scale
                                   attribute. See the attribute description for more details.
            """
            self.root.driver.acquisition.configure(sweep_mode_continuous,
                                                   number_of_sweeps,
                                                   detector_type_auto,
                                                   detector_type.value+1)

    @Namespace
    class frequency(QObject, specan_ivi_interface.SpecAnIviInterface.frequency, metaclass=QtInterfaceMetaclass):
        start_changed = Signal(float)
        stop_changed = Signal(float)
        offset_changed = Signal(float)

        @property
        def start(self):
            """
            Start frequency.

            Specifies the left edge of the frequency domain in Hertz. This is used in conjunction with the Frequency
            Stop attribute to define the frequency domain. If the Frequency Start attribute value is equal to the
            Frequency Stop attribute value then the spectrum analyzer's horizontal attributes are in time-domain.
            """
            return self.root.driver.sc.frequency_start

        @start.setter
        def start(self, value):
            self.root.driver.sc.frequency_start = value
            self.start_changed.emit(value)

        @property
        def stop(self):
            """
            Stop frequency.

            Specifies the right edge of the frequency domain in Hertz. This is used in conjunction with the Frequency
            Start attribute to define the frequency domain. If the Frequency Start attribute value is equal to the
            Frequency Stop attribute value then the spectrum analyzer's horizontal attributes are in time-domain.
            """
            return self.root.driver.sc.frequency_stop

        @stop.setter
        def stop(self, value):
            self.root.driver.sc.frequency_stop = value
            self.stop_changed.emit(value)

        @property
        def offset(self):
            """
            Frequency offset.

            Specifies an offset value, in Hertz, that is added to the frequency readout. The offset is used to
            compensate for external frequency conversion. This changes the driver's Frequency Start and Frequency Stop
            attributes.

            The equations relating the affected values are:

            Frequency Start = Actual Start Frequency + Frequency Offset
            Frequency Stop = Actual Stop Frequency + Frequency Offset
            Marker Position = Actual Marker Frequency + Frequency Offset
            """
            return self.root.driver.frequency.offset

        @offset.setter
        def offset(self, value):
            self.root.driver.frequency.offset = value
            self.offset_changed.emit(value)

        def configure_center_span(self, center_frequency, span):
            """
            This function configures the frequency range defining the center frequency and the frequency span. If the
            span corresponds to zero Hertz, then the spectrum analyzer operates in time-domain mode. Otherwise, the
            spectrum analyzer operates in frequency-domain mode.

            This function modifies the Frequency Start and Frequency Stop attributes as follows:

            Frequency Start = CenterFrequency - Span / 2
            Frequency Stop = CenterFrequency + Span / 2

            :param center_frequency: Specifies the center frequency of the frequency sweep. The units are Hertz.
            :param span: Specifies the frequency span of the frequency sweep. The units are Hertz.
            """
            self.root.driver.frequency.configure_center_span(center_frequency, span)
            self.start_changed.emit(self.start)
            self.stop_changed.emit(self.stop)

        def configure_start_stop(self, start_frequency, stop_frequency):
            """
            This function configures the frequency range defining its start frequency and its stop frequency. If the
            start frequency is equal to the stop frequency, then the spectrum analyzer operates in time-domain mode.
            Otherwise, the spectrum analyzer operates in frequency-domain mode.

            :param start_frequency: Specifies the start frequency of the frequency sweep (in Hertz). The driver uses
                                    this value to set the Frequency Start attribute. See the attribute description for
                                    more details.
            :param stop_frequency: Specifies the stop frequency of the frequency sweep (in Hertz). The driver uses this
                                   value to set the Frequency Stop attribute. See the attribute description for more
                                   details.
            """
            self.root.driver.frequency.configure_start_stop(start_frequency, stop_frequency)
            self.start_changed.emit(self.start)
            self.stop_changed.emit(self.stop)

    @Namespace
    class sweep_coupling(QObject,
                         specan_ivi_interface.SpecAnIviInterface.sweep_coupling,
                         metaclass=QtInterfaceMetaclass):
        resolution_bandwidth_changed = Signal(float)
        resolution_bandwidth_auto_changed = Signal(bool)
        sweep_time_changed = Signal(float)
        sweep_time_auto_changed = Signal(bool)
        video_bandwidth_changed = Signal(float)
        video_bandwidth_auto_changed = Signal(bool)

        @property
        def resolution_bandwidth(self):
            """
            Specifies the resolution bandwidth.

            Specifies the width of the IF filter in Hertz. For more information see Section 4.1.1, Sweep Coupling
            Overview.
            """
            return self.root.driver.sc.resolution_bandwidth

        @resolution_bandwidth.setter
        def resolution_bandwidth(self, value):
            self.root.driver.sc.resolution_bandwidth = value
            self.resolution_bandwidth_changed.emit(value)

        @property
        def resolution_bandwidth_auto(self):
            """
            Select resolution bandwidth automatically.

            If set to True, the resolution bandwidth is automatically selected. If set to False, the resolution
            bandwidth is manually selected.
            """
            return self.root.driver.sweep_coupling.resolution_bandwidth_auto

        @resolution_bandwidth_auto.setter
        def resolution_bandwidth_auto(self, value):
            self.root.driver.sweep_coupling.resolution_bandwidth_auto = value
            self.resolution_bandwidth_auto_changed.emit(value)

        @property
        def sweep_time(self):
            """
            Specifies the sweep time.

            Specifies the length of time to sweep from the left edge to the right edge of the current domain.
            The units are seconds.
            """
            return self.root.driver.sc.sweep_time

        @sweep_time.setter
        def sweep_time(self, value):
            self.root.driver.sc.sweep_time = value
            self.sweep_time_changed.emit(value)

        @property
        def sweep_time_auto(self):
            """
            Select sweep time automatically.

            If set to True, the sweep time is automatically selected If set to False, the sweep time is manually
            selected.
            """
            return self.root.driver.sweep_coupling.sweep_time_auto

        @sweep_time_auto.setter
        def sweep_time_auto(self, value):
            self.root.driver.sweep_coupling.sweep_time_auto = value
            self.sweep_time_auto_changed.emit(value)

        @property
        def video_bandwidth(self):
            """
            Specifies the video bandwidth of the post-detection filter in Hertz.
            """
            return self.root.driver.sweep_coupling.video_bandwidth

        @video_bandwidth.setter
        def video_bandwidth(self, value):
            self.root.driver.sweep_coupling.video_bandwidth = value
            self.video_bandwidth_changed.emit(value)

        @property
        def video_bandwidth_auto(self):
            """
            Select video bandwidth automatically.

            If set to True, the video bandwidth is automatically selected. If set to False, the video bandwidth is
            manually selected.
            """
            return self.root.driver.sweep_coupling.video_bandwidth_auto

        @video_bandwidth_auto.setter
        def video_bandwidth_auto(self, value):
            self.root.driver.sweep_coupling.video_bandwidth_auto = value
            self.video_bandwidth_auto_changed.emit(value)

        def configure(self, resolution_bandwidth, video_bandwidth, sweep_time):
            """
            This function configures the coupling and sweeping attributes. For additional sweep coupling information
            refer to Section 4.1.1, Sweep Coupling Overview.

            :param resolution_bandwidth: either boolean True, Enables resolution bandwidth auto coupling. The
                                                         driver uses this value to set the Resolution Bandwidth Auto
                                                         attribute. See the attribute description for more details.
                                         or float, Specifies the measurement resolution bandwidth in Hertz. The driver
                                                   uses this value to set the Resolution Bandwidth attribute and
                                                   disables auto coupling. See the attribute description for more
                                                   details.
            :param video_bandwidth: either boolean True, Enables video bandwidth auto coupling. The driver uses
                                                    this value to set the Video Bandwidth Auto attribute. See the
                                                    attribute description for more details.
                                    or float, Specifies the video bandwidth of the postdetection filter in Hertz.
                                              The driver uses this value to set the Video Bandwidth attribute and
                                              disables auto coupling. See the attribute description for more details.
            :param sweep_time: either boolean True, Enables sweep time auto coupling. The driver uses this value
                                               to set the Sweep Time Auto attribute. See the attribute description for
                                               more details.
                               or float, Specifies the length of time to sweep from the left edge to the right edge of
                                         the current domain. Units are seconds. The driver uses this value to set the
                                         Sweep Time attribute and disables auto coupling. See the attribute description
                                         for more details.
            """
            resolution_bandwidth_auto = False
            video_bandwidth_auto = False
            sweep_time_auto = False
            if resolution_bandwidth == True:
                resolution_bandwidth_auto = True
                resolution_bandwidth = 0
            if video_bandwidth == True:
                video_bandwidth_auto = True
                video_bandwidth = 0
            if sweep_time == True:
                sweep_time_auto = True
                sweep_time = 0

            self.root.driver.sweep_coupling.configure(resolution_bandwidth_auto,
                                                      resolution_bandwidth,
                                                      video_bandwidth_auto,
                                                      video_bandwidth,
                                                      sweep_time_auto,
                                                      sweep_time)

            self.resolution_bandwidth_auto_changed.emit(resolution_bandwidth_auto)
            self.resolution_bandwidth_changed.emit(resolution_bandwidth)
            self.video_bandwidth_auto_changed.emit(video_bandwidth_auto)
            self.video_bandwidth_changed.emit(video_bandwidth)
            self.sweep_time_auto_changed.emit(sweep_time_auto)
            self.sweep_time_changed.emit(sweep_time)

    class trace(specan_ivi_interface.SpecAnIviInterface.trace):
        """
        Repeated capability, attribute name traces.
        """
        @property
        def name(self):
            """
            Name of trace.

            Returns the physical repeated capability identifier defined by the specific driver for the trace that
            corresponds to the index that the user specifies. If the driver defines a qualified trace name, this
            property returns the qualified name.
            """
            self.root.driver.sc.trace_idx = self.index + 1
            return self.root.driver.sc.trace_name

        @property
        def type(self):
            """
            Specifies the representation of the acquired data.
            """
            self.root.driver.sc.trace_idx = self.index + 1
            return specan_ivi_interface.TraceType(self.root.driver.sc.tr_type - 1)

        @type.setter
        def type(self, value):
            self.root.driver.sc.trace_idx = self.index + 1
            self.root.driver.sc.tr_type = value.value + 1

        def fetch_y(self):
            """
            Fetches y values from last measurement.

            This function returns the trace the spectrum analyzer acquires. The trace is from a previously initiated
            acquisition. The user calls the Initiate function to start an acquisition. The user calls the
            Acquisition Status function to determine when the acquisition is complete.

            The user may call the Read Y Trace function instead of the Initiate function. This function starts an
            acquisition, waits for the acquisition to complete, and returns the trace in one function call.

            The Amplitude array returns data that represents the amplitude of the signals obtained by sweeping from
            the start frequency to the stop frequency (in frequency domain, in time domain the amplitude array is
            ordered from beginning of sweep to end). The Amplitude Units attribute determines the units of the points
            in the Amplitude array.

            This function does not check the instrument status. The user calls the Error Query function at the
            conclusion of the sequence to check the instrument status.

            :return: (numpy array of frequencies, numpy array of amplitude values)
            """
            self.root.driver.sc.trace_idx = self.index + 1
            with safearray_as_ndarray:
                return self.root.driver.sc.fetch()

        def read_y(self, maximum_time):
            """
            Read y values after initiating an acquisition.

            This function initiates a signal acquisition based on the present instrument configuration. It then waits
            for the acquisition to complete, and returns the trace as an array of amplitude values. The amplitude array
            returns data that represent the amplitude of the signals obtained by sweeping from the start frequency to
            the stop frequency (in frequency domain, in time domain the amplitude array is ordered from beginning of
            sweep to end). The Amplitude Units attribute determines the units of the points in the amplitude array.
            This function resets the sweep count.

            If the spectrum analyzer did not complete the acquisition within the time period the user specified with
            the MaxTime parameter, the function raises the Max Time Exceeded error.

            :param maximum_time: MAX_TIME_IMMEDIATE: The function returns immediately. If no valid measurement value
                                                     exists, the function raises an error.
                                 MAX_TIME_INDEFINITE: The function waits indefinitely for the measurement to complete.
                                 otherwise: time the functions waits before raising a timeout error in milliseconds.
            :return: (numpy array of frequencies, numpy array of amplitude values)
            """
            self.root.driver.sc.trace_idx = self.index + 1
            with safearray_as_ndarray:
                y_trace = self.root.driver.traces[self.name].read_y(int(maximum_time))
            if self.root.frequency.start == self.root.frequency.stop:
                x_start = 0
                x_stop = self.root.sweep_coupling.sweep_time
            else:
                x_start = self.root.frequency.start
                x_stop = self.root.frequency.stop
            size = self.root.driver.traces[self.root.driver.sc.trace_name].size
            x_trace = numpy.linspace(x_start, x_stop, size, True)
            return x_trace, y_trace

    class traces(specan_ivi_interface.SpecAnIviInterface.traces):
        def initiate(self):
            """
            This function initiates an acquisition.

            After calling this function, the spectrum analyzer leaves the idle state.

            This function does not check the instrument status. The user calls the Acquisition Status function to
            determine when the acquisition is complete.
            """
            self.root.driver.session.traces.Initiate()

        def abort(self):
            """
            Aborts a running measurement.

            This function aborts a previously initiated measurement and returns the spectrum analyzer to the idle
            state. This function does not check instrument status.
            """
            self.root.driver.session.traces.Abort()

        def acquisition_status(self):
            """
            This function determines and returns the status of an acquisition.
            """
            return specan_ivi_interface.AcquisitionStatus(self.root.driver.session.traces.AcquisitionStatus())


# endregion
# region Extensions


class MultitraceExtension(specan_ivi_interface.MultitraceExtensionInterface):
    """
    Extension IVI methods for spectrum analyzers supporting simple mathematical operations on traces
    """
    class traces:
        @Namespace
        class math(QObject,
                   specan_ivi_interface.MultitraceExtensionInterface.traces.math,
                   metaclass=QtInterfaceMetaclass):
            """
            The math namespace is supposed to be implemented as traces.math and not as repeated capability.
            """
            def add(self, dest_trace, trace1, trace2):
                """
                Adds two traces.

                This function modifies a trace to be the point by point sum of two other traces. Any data in the
                destination trace is deleted.

                DestinationTrace = Trace1 + Trace2

                :param dest_trace: Specifies the name of the result
                :param trace1: Specifies the name of first trace operand.
                :param trace2: Specifies the name of the second trace operand.
                :return:
                """
                self.root.driver.traces.math.add(dest_trace, trace1, trace2)

            def copy(self, dest_trace, src_trace):
                """
                Copies a trace.

                This function copies the data array from one trace into another trace. Any data in the Destination
                Trace is deleted.

                :param dest_trace: Specifies the name of the trace into which the array is copied.
                :param src_trace: Specifies the name of the trace to be copied.
                :return:
                """
                self.root.driver.traces.math.copy(dest_trace, src_trace)

            def exchange(self, trace1, trace2):
                """
                Exchanges two traces.

                This function exchanges the data arrays of two traces.

                :param trace1: Specifies the name of the first trace to be exchanged.
                :param trace2: Specifies the name of the second trace to be exchanged.
                :return:
                """
                self.root.driver.traces.math.exchange(trace1, trace2)

            def subtract(self, dest_trace, trace1, trace2):
                """
                Subtracts two traces.

                This function modifies a trace to be the point by point difference of two other traces. Any data in the
                destination trace is deleted.

                DestinationTrace = Trace1 - Trace2

                :param dest_trace: Specifies the name of the result
                :param trace1: Specifies the name of first trace operand.
                :param trace2: Specifies the name of the second trace operand.
                :return:
                """
                self.root.driver.traces.math.subtract(dest_trace, trace1, trace2)


class MarkerExtension(specan_ivi_interface.MarkerExtensionInterface):
    """
    The IviSpecAnMarker extension group supports spectrum analyzers that have markers. Markers are applied
    to traces and used for a wide range of operations. Some operations are simple, such as reading an
    amplitude value at an X-axis position, while others operations are complex, such as signal tracking.
    """

    class marker(specan_ivi_interface.MarkerExtensionInterface.marker):
        """
        Contains all marker functions. Repeated namespace.
        """
        enabled_changed = Signal(bool)
        position_changed = Signal(float)
        threshold_changed = Signal(float)
        trace_changed = Signal(str)
        peak_excursion_changed = Signal(float)
        signal_track_enabled_changed = Signal(bool)

        @property
        def amplitude(self):
            """
            Marker amplitude.

            Returns the amplitude of the marker. The units are specified by the Amplitude Units attribute, except
            when the Marker Type attribute is set to Delta. Then the units are dB. If the Marker Enabled attribute is
            set to False, any attempt to read this attribute returns the Marker Not Enabled error.
            :return: Query Marker
            """
            self.root.driver.marker.active_marker = self.name
            return self.root.driver.marker.amplitude

        @property
        def enabled(self):
            """
            Marker enabled.

            If set to True, the  marker is enabled. When False, the marker is disabled.
            """
            self.root.driver.marker.active_marker = self.name
            return self.root.driver.marker.enabled

        @enabled.setter
        def enabled(self, value):
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.enabled = value
            self.enabled_changed.emit(value)

        @Namespace
        class frequency_counter(QObject,
                                specan_ivi_interface.MarkerExtensionInterface.marker.frequency_counter,
                                metaclass=QtInterfaceMetaclass):
            enabled_changed = Signal(bool)
            resolution_changed = Signal(float)

            @property
            def enabled(self):
                """
                Frequency counter enabled.

                Enables/disables the marker frequency counter for greater marker measurement accuracy. If set to True,
                the marker frequency counter is enabled. If set to False, the marker frequency counter is disabled. This
                attribute returns the Marker Not Enabled error if the Marker Enabled attribute is set to False..
                """
                self.root.driver.marker.active_marker = self.parent_namespace.name
                return self.root.driver.marker.frequency_counter.enabled

            @enabled.setter
            def enabled(self, value):
                self.root.driver.marker.active_marker = self.parent_namespace.name
                self.root.driver.marker.frequency_counter.enabled = value
                self.enabled_changed.emit(value)

            @property
            def resolution(self):
                """
                Frequency counter resolution.

                Specifies the resolution of the frequency counter in Hertz. The measurement gate time is the reciprocal
                of the specified resolution.
                """
                self.root.driver.marker.active_marker = self.parent_namespace.name
                return self.root.driver.marker.frequency_counter.resolution

            @resolution.setter
            def resolution(self, value):
                self.root.driver.marker.active_marker = self.parent_namespace.name
                self.root.driver.marker.frequency_counter.resolution = value
                self.resolution_changed.emit(value)

            def configure(self, enabled, resolution):
                """
                This function sets the marker frequency counter resolution and enables or disables the marker frequency
                counter.

                :param enabled: Enables or disables the marker frequency counter. The driver uses this value to set
                                the Marker Frequency Counter Enabled attribute. See the attribute description for more
                                details.
                :param resolution: Specifies the frequency counter resolution in Hertz. This value is ignored when
                                   Enabled is False. The driver uses this value to set the Marker Frequency Counter
                                   Resolution attribute. See the attribute description for more details.
                :return:
                """
                self.root.driver.marker.active_marker = self.parent_namespace.name
                self.root.driver.marker.frequency_counter.configure(enabled, resolution)
                self.enabled_changed.emit(enabled)
                self.resolution_changed.emit(resolution)

        @property
        def name(self):
            """
            This property returns the marker identifier.
            """
            return self.root.driver.marker.name(self.index + 1)

        @property
        def position(self):
            """
            Marker position.

            Specifies the frequency in Hertz or time position in seconds of the marker (depending on the mode in
            which the analyzer is operating, frequency or time-domain). This attribute returns the Marker Not
            Enabled error if the marker is not enabled.
            """
            self.root.driver.marker.active_marker = self.name
            return self.root.driver.marker.position

        @position.setter
        def position(self, value):
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.position = value
            self.position_changed.emit(value)

        @property
        def threshold(self):
            """
            Specifies the lower limit of the search domain vertical range for the Marker Search function.
            """
            self.root.driver.marker.active_marker = self.name
            return self.root.driver.marker.threshold

        @threshold.setter
        def threshold(self, value):
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.threshold = value
            self.threshold_changed.emit(value)

        @property
        def trace(self):
            """
            Specifies the Trace for the marker.
            """
            self.root.driver.marker.active_marker = self.name
            return self.root.driver.marker.trace

        @trace.setter
        def trace(self, value):
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.trace = value
            self.trace_changed.emit(value)

        @property
        def peak_excursion(self):
            """
            Specifies the minimum amplitude variation of the signal in dB that the Marker Search function can
            identify as a peak.
            """
            self.root.driver.marker.active_marker = self.name
            return self.root.driver.marker.peak_excursion

        @peak_excursion.setter
        def peak_excursion(self, value):
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.peak_excursion = value
            self.peak_excursion_changed.emit(value)

        @property
        def signal_track_enabled(self):
            """
            Track the signal.

            If set to True, the spectrum analyzer centers the signal after each sweep. This process invalidates the
            Frequency Start and Frequency Stop attributes. If set to False, the spectrum analyzer does not center
            the signal after each sweep.

            Operations on this attribute return the Marker Not Enabled error if the marker is not enabled.

            Note: Signal tracking can only be enabled on one marker at any given time. The driver is responsible for
            enforcing this policy
            """
            self.root.driver.marker.active_marker = self.name
            return self.root.driver.marker.signal_track_enabled

        @signal_track_enabled.setter
        def signal_track_enabled(self, value):
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.signal_track_enabled = value
            self.signal_track_enabled_changed.emit(value)

        def configure_enabled(self, enabled, trace):
            """
            This function enables the marker on the specified Trace.

            :param enabled: Enables or disables the marker. The driver uses this value to set the Marker Enabled
                            attribute. See the attribute description for more details.
            :param trace: Specifies the trace name. The driver uses this value to set the Marker Trace attribute.
                          See the attribute description for more details.
            :return:
            """
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.configure_enabled(enabled, trace)
            self.enabled_changed.emit(enabled)
            self.trace_changed.emit(trace)

        def configure_search(self, peak_excursion, marker_threshold):
            """
            This function configures the Peak Excursion and Marker Threshold attribute values.

            :param peak_excursion: Minimum amplitude variation of the signal that the marker can recognize as a peak
                                   in dB. The driver uses this value to set the Peak Excursion attribute. See the
                                   attribute description for more details.
            :param marker_threshold: Minimum amplitude below which a peak will not be detected. The driver uses this
                                     value to set the Marker Threshold attribute. See the attribute description for
                                     more details.
            :return:
            """
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.configure_search(peak_excursion, marker_threshold)
            self.peak_excursion_changed.emit(peak_excursion)
            self.threshold_changed.emit(marker_threshold)

        def search(self, search_type):
            """
            This function specifies the type of marker search and performs the search. This function returns the Marker
            Not Enabled error if the Marker Enabled attribute is set to False.

            :param search_type: Specifies the type of marker search.
            """
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.search(search_type.value + 1)

        def query(self):
            """
            This function returns the horizontal position and the amplitude level of the marker.

            :return: set (marker position, marker amplitude)
            """
            self.root.driver.marker.active_marker = self.name
            return set(self.root.driver.marker.query())

    class markers(specan_ivi_interface.MarkerExtensionInterface.markers):
        def disable_all(self):
            """
            This function disables all markers.
            """
            self.root.driver.marker.disable_all()


class TriggerExtension(specan_ivi_interface.TriggerExtensionInterface):
    """
    This extension group specifies the source of the trigger signal that causes the analyzer to leave the
    Wait-For-Trigger state.
    """
    class trigger(specan_ivi_interface.TriggerExtensionInterface.trigger):
        source_changed = Signal(specan_ivi_interface.TriggerSource)

        @property
        def source(self):
            """
            Specifies the source of the trigger signal that causes the analyzer to leave the Wait-For-Trigger state.
            """
            return specan_ivi_interface.TriggerSource(self.root.driver.trigger.source - 1)

        @source.setter
        def source(self, value):
            self.root.driver.trigger.source = value.value + 1
            self.source_changed.emit(value)


class ExternalTriggerExtension(specan_ivi_interface.ExternalTriggerExtensionInterface):
    """
    This extension group specifies the external trigger level and external trigger slope when the Trigger Source
    Attribute is set to external, which causes the analyzer to leave the Wait-For-Trigger state.
    """
    class trigger:
        class external(QObject,
                       specan_ivi_interface.ExternalTriggerExtensionInterface.trigger.external,
                       metaclass=QtInterfaceMetaclass):
            level_changed = Signal(float)
            slope_changed = Signal(specan_ivi_interface.Slope)

            @property
            def level(self):
                """
                Specifies the level, in Volts, that the external trigger signal shall reach to trigger the acquisition.
                """
                return self.root.driver.trigger.external.level

            @level.setter
            def level(self, value):
                self.root.driver.trigger.external.level = value
                self.level_changed.emit(value)

            @property
            def slope(self):
                """
                Specifies which slope of the external trigger signal triggers the acquisition.

                See also: Slope.
                """
                return specan_ivi_interface.Slope(self.root.driver.trigger.external.slope - 1)

            @slope.setter
            def slope(self, value):
                self.root.driver.trigger.external.slope = value.value + 1
                self.slope_changed.emit(value)

            def configure(self, level, slope):
                """
                This function specifies at which level and slope of the external trigger signal, acquisition is
                triggered. This is applicable when the Trigger Source attribute is set to External.

                :param level: Specifies the level, in volts, that the external trigger signal shall reach to trigger
                              the acquisition. The driver uses this value to set the External Trigger Level attribute.
                              See the attribute description for more details
                :param slope: Specifies which slope of the external trigger signal triggers the acquisition. The driver
                              uses this value to set the External Trigger Slope attribute. See the attribute
                              description for more details.
                :return:
                """
                self.root.driver.trigger.external.configure(level, slope)
                self.level_changed.emit(level)
                self.slope_changed.emit(slope)


class SoftwareTriggerExtension(specan_ivi_interface.SoftwareTriggerExtensionInterface):
    """
    The IviSpecAnSoftwareTrigger Extension Group supports spectrum analyzers that can acquire traces based
    on a software trigger signal. The user can send a software trigger to cause signal output to occur.

    This extension affects instrument behavior when the Trigger Source attribute is set to Software.
    """
    class traces(specan_ivi_interface.SoftwareTriggerExtensionInterface.traces):
        def send_software_trigger(self):
            """
            Sends a software trigger to the instrument.

            This function sends a software-generated trigger to the instrument. It is only applicable for instruments using
            interfaces or protocols which support an explicit trigger function. For example, with GPIB this function could
            send a group execute trigger to the instrument. Other implementations might send a *TRG command.

            Since instruments interpret a software-generated trigger in a wide variety of ways, the precise response of the
            instrument to this trigger is not defined. Note that SCPI details a possible implementation.

            This function should not use resources which are potentially shared by other devices (for example, the VXI
            trigger lines). Use of such shared resources may have undesirable effects on other devices.

            This function should not check the instrument status. Typically, the end-user calls this function only in a
            sequence of calls to other low-level driver functions. The sequence performs one operation. The end-user uses
            the low-level functions to optimize one or more aspects of interaction with the instrument. To check the
            instrument status, call the appropriate error query function at the conclusion of the sequence.

            The trigger source attribute must accept Software Trigger as a valid setting for this function to work. If the
            trigger source is not set to Software Trigger, this function does nothing and returns the error Trigger Not
            Software

            :return: TriggerNotSoftwareException if trigger source is not set to software.
            """
            self.root.driver.session.traces.SendSoftwareTrigger()


class VideoTriggerExtension(specan_ivi_interface.VideoTriggerExtensionInterface):
    """
    This extension group specifies the video trigger level and video trigger slope when the Trigger Source
    attribute is set to Video, which causes the analyzer to leave the Wait-For-Trigger state.
    """
    class trigger:
        class video(QObject,
                    specan_ivi_interface.VideoTriggerExtensionInterface.trigger.video,
                    metaclass=QtInterfaceMetaclass):
            level_changed = Signal(float)
            slope_changed = Signal(specan_ivi_interface.Slope)

            @property
            def level(self):
                """
                Specifies the level that the video signal shall reach to trigger the acquisition.

                The units are specified by the Amplitude Units attribute.
                """
                return self.root.driver.trigger.video.level

            @level.setter
            def level(self, value):
                self.root.driver.trigger.video.level = value
                self.level_changed.emit(value)

            @property
            def slope(self):
                """
                Specifies which slope of the video signal triggers the acquisition.

                Possible values: Slope Enum.
                """
                return specan_ivi_interface.Slope(self.root.driver.trigger.video.slope - 1)

            @slope.setter
            def slope(self, value):
                self.root.driver.trigger.video.slope = value.value + 1
                self.slope_changed.emit(value)

            def configure(self, level, slope):
                """
                This function specifies at which level and slope of the video trigger signal, acquisition is
                triggered. This is applicable when the Trigger Source attribute is set to Video.

                :param level: Specifies the level, in volts, that the video trigger signal shall reach to trigger
                              the acquisition. The driver uses this value to set the Video Trigger Level attribute.
                              See the attribute description for more details
                :param slope: Specifies which slope of the video trigger signal triggers the acquisition. The driver
                              uses this value to set the Video Trigger Slope attribute. See the attribute
                              description for more details.
                :return:
                """
                self.root.driver.trigger.video.configure(level, slope.value - 1)
                self.level_changed.emit(level)
                self.slope_changed.emit(slope)


class DisplayExtension(specan_ivi_interface.DisplayExtensionInterface):
    """
    The IviSpecAnDisplay extension group controls the display related attributes.
    """
    class display(QObject,
                  specan_ivi_interface.DisplayExtensionInterface.display,
                  metaclass=QtInterfaceMetaclass):
        units_per_division_changed = Signal(float)

        @property
        def number_of_divisions(self):
            """
            Specifies the number of vertical screen divisions.
            """
            return self.root.driver.display.number_of_divisions

        @property
        def units_per_division(self):
            """
            Specifies the number of vertical units in one screen division.

            This attribute is typically used in conjunction with the Reference Level attribute to set the vertical
            range of the spectrum analyzer.
            """
            return self.root.driver.display.units_per_division

        @units_per_division.setter
        def units_per_division(self, value):
            self.root.driver.display.units_per_division = value
            self.units_per_division_changed.emit(value)


class MarkerTypeExtension(specan_ivi_interface.MarkerTypeExtensionInterface):
    """
    The IviSpecAnMarkerType extension group provides support for analyzers that have multiple marker types.
    """
    class marker(specan_ivi_interface.MarkerTypeExtensionInterface.marker):
        @property
        def type(self):
            """
            Specifies the marker type of the marker.

            See also: MarkerType
            """
            self.root.driver.marker.active_marker = self.name
            return specan_ivi_interface.MarkerType(self.root.driver.marker.type - 1)


class DeltaMarkerExtension(specan_ivi_interface.DeltaMarkerExtensionInterface):
    """
    The IviSpecAnDeltaMarker extension group provides delta-marker capabilities.

    This section supports analyzers that have delta-marker capabilities. A delta marker has the same properties
    as a normal marker except that its position and amplitude are relative to a fixed reference point. This
    reference point is defined when the marker is converted from a normal marker to a delta marker.
    """
    class marker(specan_ivi_interface.DeltaMarkerExtensionInterface.marker):
        type_changed = Signal(specan_ivi_interface.MarkerType)

        @property
        def reference_amplitude(self):
            """
            Amplitude of the reference marker.

            Specifies the reference marker amplitude when the active marker is a delta marker. The unit is given by the
            Amplitude Units attribute.

            If the Marker Type attribute is not Delta, this property raises the NotDeltaMarkerException.
            """
            if self.type != specan_ivi_interface.MarkerType.DELTA:
                raise specan_ivi_interface.NotDeltaMarkerException('The marker {0} is not a delta marker.'.format(
                    self.name))
            self.root.driver.marker.active_marker = self.name
            return self.root.driver.marker.reference_amplitude

        @property
        def reference_position(self):
            """
            Position of the reference marker.

            Specifies the position of the reference marker, when the active marker is a delta marker. The units are
            Hertz for frequency domain measurements, and seconds for time domain measurements.

            If the Marker Type attribute is not Delta, this property raises the NotDeltaMarkerException.
            """
            if self.type != specan_ivi_interface.MarkerType.DELTA:
                raise specan_ivi_interface.NotDeltaMarkerException('The marker {0} is not a delta marker.'.format(
                    self.name))
            self.root.driver.marker.active_marker = self.name
            return self.root.driver.marker.reference_position

        def make_delta(self, value):
            """
            This function specifies whether the active marker is a delta marker.

            When the DeltaMarker parameter is True, the Marker Type attribute is set to Delta. The Reference Marker
            Amplitude and Reference Marker Position attributes are set with the active marker current Marker Amplitude
            and Marker Position attribute respectively.

            While the marker remains a delta marker, the values of the Marker Amplitude and Marker Position attributes
            will be relative to the Reference Marker Amplitude and Reference Marker Position attributes, respectively.

            When the DeltaMarker parameter is False, the active marker is changed to a normal marker. The Marker
            Type attribute is set to Normal. The Marker Amplitude and Marker Position attributes are returned to a
            normal state and are no longer relative to the Reference Marker Amplitude and Reference Marker Position
            attributes.
            """
            self.root.driver.marker.active_marker = self.name
            self.root.driver.marker.make_delta(value)
            self.type_changed.emit(self.type)

        @property
        def query_reference(self):
            """
            This function returns the amplitude and position of the reference marker. If the Marker Type attribute is
            not Delta, this function returns the Not Delta Marker error.

            :return: set of reference position and amplitude
            """
            if self.type != specan_ivi_interface.MarkerType.DELTA:
                raise specan_ivi_interface.NotDeltaMarkerException('The marker {0} is not a delta marker.'.format(
                    self.name))
            self.root.driver.marker.active_marker = self.name
            return set(self.root.driver.marker.query_reference())


class ExternalMixerExtension(specan_ivi_interface.ExternalMixerExtensionInterface):
    """
    The IviSpecAnExternalMixer extension group provides support for external mixers.

    Many spectrum analyzers have outputs and inputs that allow external equipment to use the IF or mixer signal that
    the spectrum analyzer uses. In this case, external equipment can be used to mix signals to convert them to
    measurable frequencies. This allows the use of an analyzer to measure values that are outside of the normal
    frequency range of the equipment. When using an external mixer, many of the settings of the analyzer have to be
    carefully converted to allow the user to know what is meant by the values read. Specifically, the frequency,
    the harmonic number, mixer configuration, and conversion loss must be configured carefully to be able to use
    the external mixing successfully.

    The frequency of the input signal can be expressed as a function of the local oscillator (LO) frequency and
    the selected harmonic of the 1st LO is as follows:
        fin = n * fLO +/- fIF
            Where: fin frequency of input signal
                       n order of harmonic used for conversion
                   fLO frequency of 1st LO
                   fIF intermediate frequency

    The Harmonic number defines the order n of the harmonic used for conversion. Both even and odd harmonics can be
    used. The selected harmonic, together with the setting range of the 1st LO, determines the limits of the settable
    frequency range. The following applies:
        Lower frequency limit: fmin = n * fLO,min - fIF
        Upper frequency limit: fmax = n * fLO,max + fIF
            Where: fLO,min lower frequency limit of LO
        fLO,max upper frequency limit of LO
    The following sections describe the mixer configuration and the conversion loss table configuration.
    """
    class external_mixer(QObject,
                         specan_ivi_interface.ExternalMixerExtensionInterface.external_mixer,
                         metaclass=QtInterfaceMetaclass):
        enabled_changed = Signal(bool)
        average_conversion_loss_changed = Signal(float)
        harmonic_changed = Signal(float)
        number_of_ports_changed = Signal(int)

        @property
        def enabled(self):
            """
            Enables external mixer.

            If set to True, the external mixer is enabled. If set to False, the external mixer is disabled.
            """
            return self.root.driver.external_mixer.enabled

        @enabled.setter
        def enabled(self, value):
            self.root.driver.external_mixer.enabled = value
            self.enabled_changed.emit(value)

        @property
        def average_conversion_loss(self):
            """
            Specifies the average conversion loss.
            """
            return self.root.driver.external_mixer.average_conversion_loss

        @average_conversion_loss.setter
        def average_conversion_loss(self, value):
            self.root.driver.external_mixer.average_conversion_loss = value
            self.average_conversion_loss_changed.emit(value)

        @property
        def harmonic(self):
            """
            Specifies the order n of the harmonic used for conversion.
            """
            return self.root.driver.external_mixer.harmonic

        @harmonic.setter
        def harmonic(self, value):
            self.root.driver.external_mixer.harmonic = value
            self.harmonic_changed.emit(value)

        @property
        def number_of_ports(self):
            """
            Specifies the number of mixer ports.
            """
            return self.root.driver.external_mixer.number_of_ports

        @number_of_ports.setter
        def number_of_ports(self, value):
            self.root.driver.external_mixer.number_of_ports = value
            self.number_of_ports_changed.emit(value)

        def configure(self, harmonic, average_conversion_loss):
            """
            This function specifies the mixer harmonic and average conversion loss.

            :param harmonic: Specifies the harmonic number. The driver uses this value to set the External Mixer
                             Harmonic attribute. See the attribute description for more details.
            :param average_conversion_loss: Specifies the average conversion loss. The driver uses this value to set
                                            the External Mixer Average Conversion Loss attribute. See the attribute
                                            description for more details.
            :return:
            """
            self.root.driver.external_mixer.configure(harmonic, average_conversion_loss)
            self.harmonic_changed.emit(harmonic)
            self.average_conversion_loss_changed.emit(average_conversion_loss)

        class bias(QObject,
                   specan_ivi_interface.ExternalMixerExtensionInterface.external_mixer.bias,
                   metaclass=QtInterfaceMetaclass):
            level_changed = Signal(float)
            enabled_changed = Signal(bool)
            limit_changed = Signal(float)

            @property
            def level(self):
                """
                Specifies the bias current in Amps.
                """
                return self.root.driver.external_mixer.bias.level

            @level.setter
            def level(self, value):
                self.root.driver.external_mixer.bias.level = value
                self.level_changed.emit(value)

            @property
            def enabled(self):
                """
                Bias enabled.

                If set to True, the external mixer bias is enabled. If set to False, the external mixer bias
                is disabled.
                """
                return self.root.driver.external_mixer.bias.enabled

            @enabled.setter
            def enabled(self, value):
                self.root.driver.external_mixer.bias.enabled = value
                self.enabled_changed.emit(value)

            @property
            def limit(self):
                """
                Bias current limit.

                Specifies the bias current limit in Amps.
                """
                return self.root.driver.external_mixer.bias.limit

            @limit.setter
            def limit(self, value):
                self.root.driver.external_mixer.bias.limit = value
                self.limit_changed.emit(value)

            def configure(self, bias, bias_limit):
                """
                Configures external mixer bias.

                This function configures the external mixer bias and the external mixer bias limit.

                :param bias: Specifies the bias current. The driver uses this value to set the External Mixer Bias
                             attribute. See the attribute description for more details.
                :param bias_limit: Specifies the bias current limit. The driver uses this value to set the External
                                   Mixer Bias Limit attribute. See the attribute description for more details.
                :return:
                """
                self.root.driver.external_mixer.bias.configure(bias, bias_limit)
                self.level_changed.emit(bias)
                self.limit_changed.emit(bias_limit)

        class conversion_loss_table(QObject,
                                    specan_ivi_interface.ExternalMixerExtensionInterface.external_mixer.conversion_loss_table,
                                    metaclass=QtInterfaceMetaclass):
            enabled_changed = Signal(bool)

            @property
            def enabled(self):
                """
                Conversion loss table enabled.

                If set to True, the conversion loss table is enabled. If set to False, the conversion loss table is
                disabled.
                """
                return self.root.driver.external_mixer.conversion_loss_table.enabled

            @enabled.setter
            def enabled(self, value):
                self.root.driver.external_mixer.conversion_loss_table.enabled = value
                self.enabled_changed.emit(value)

            def configure(self, frequency, conversion_loss):
                """
                Configures conversion loss table.

                This function configures the conversion loss table by specifying a series of frequency and a power loss
                pairs.

                :param frequency: array. Specifies the frequency values for the pairs.
                :param conversion_loss: array. Specifies the conversion loss values for the pairs.
                :return:
                """
                self.root.driver.external_mixer.conversion_loss_table.configure(frequency, conversion_loss)


class PreselectorExtension(specan_ivi_interface.PreselectorExtensionInterface):
    """
    The IviSpecAnPreselector extension controls preselectors.

    Preselectors are a network of filters and preamplifiers that are built into one unit for reducing noise and
    increasing dynamic range of an analyzer.  Preselectors are often separate instruments, but they are instruments that
    only work with spectrum analyzers. Some analyzers have internal preselectors.
    """
    class preselector(QObject,
                      specan_ivi_interface.PreselectorExtensionInterface.preselector,
                      metaclass=QtInterfaceMetaclass):
        def peak(self):
            """
            Adjusts the preselector.

            This function adjusts the preselector to obtain the maximum readings for the current start and stop
            frequency. This function may affect the marker configuration.
            """
            return self.root.driver.preselector.peak()

# endregion


class PyIviSpecAn(PyIviBase, _Specan):
    """
        Module for accessing arbitrary waveform / function generators via PythonIVI library.

        Config options:
        - driver : str module.class name of driver within the python IVI library
                       e.g. 'ivi.tektronix.tektronixAWG5000.tektronixAWG5002c'
        - uri : str unique remote identifier used to connect to instrument.
                    e.g. 'TCPIP::192.168.1.1::INSTR'
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
        this enables setting data from dynamic descriptors

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
        """
        Event handler called when module is activated.
        """
        super().on_activate()  # connects to instrument

        # find all base classes of driver
        driver_capabilities = self.driver.identity.group_capabilities.split(',')

        # dynamic class generator
        class IviTracesMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if 'IviSpecAnMultitrace' in driver_capabilities:
                    bases += (MultitraceExtension.traces, )
                if 'IviSpecAnSoftwareTrigger' in driver_capabilities:
                    bases += (SoftwareTriggerExtension.traces,)
                return super().__new__(mcs, name, bases, attrs)

        class IviTraces(list, _Specan.traces, metaclass=IviTracesMetaclass):
            def __init__(self, parent):
                super().__init__()
                self.parent_namespace = parent
                self.root = parent

        self.traces = Namespace.repeat(len(self.driver.traces), IviTraces(self))(_Specan.trace)

        if 'IviSpecAnMarker' in driver_capabilities:
            class IviMarkerMetaclass(QtInterfaceMetaclass):
                def __new__(mcs, name, bases, attrs):
                    if 'IviSpecAnMarkerType' in driver_capabilities:
                        bases += (MarkerTypeExtension.marker, )
                    if 'IviSpecAnDeltaMarker' in driver_capabilities:
                        bases += (DeltaMarkerExtension.marker, )
                    return super().__new__(mcs, name, bases, attrs)

            class IviMarker(QObject, MarkerExtension.marker, metaclass=IviMarkerMetaclass):
                pass

            class IviMarkersMetaclass(QtInterfaceMetaclass):
                def __new__(mcs, name, bases, attrs):
                    if 'IviSpecAnMarker' in driver_capabilities:
                        bases += (MarkerExtension.markers, )
                    return super().__new__(mcs, name, bases, attrs)

            class IviMarkers(list, metaclass=IviMarkersMetaclass):
                def __init__(self, parent):
                    super().__init__()
                    self.parent_namespace = parent
                    self.root = parent

            self.markers = Namespace.repeat(self.driver.marker.count, IviMarkers(self))(IviMarker)

        class IviTriggerMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if 'IviSpecAnTrigger' in driver_capabilities:
                    bases += (TriggerExtension.trigger, )
                if 'IviSpecAnExternalTrigger' in driver_capabilities:
                    bases += (ExternalTriggerExtension.trigger, )
                if 'IviSpecAnVideoTrigger' in driver_capabilities:
                    bases += (VideoTriggerExtension.trigger, )
                return super().__new__(mcs, name, bases, attrs)

        class IviTrigger(QObject, metaclass=IviTriggerMetaclass):
            external = Namespace(ExternalTriggerExtension.trigger.external)

        self.trigger = Namespace(IviTrigger)

        if 'IviSpecAnDisplay' in driver_capabilities:
            self.display = Namespace(DisplayExtension.display)

        if 'IviSpecAnExternalMixer' in driver_capabilities:
            self.external_mixer = Namespace(ExternalMixerExtension.external_mixer)

        if 'IviSpecAnPreselector' in driver_capabilities:
            self.preselector = Namespace(PreselectorExtension.preselector)