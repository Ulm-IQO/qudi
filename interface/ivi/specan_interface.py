# -*- coding: utf-8 -*-
"""
This file contains the specan interface.

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

FIXME:
- initiate, acquisition status and abort are part of acquisition but should be part of traces

"""

import abc
from core.util.interfaces import InterfaceMetaclass
from enum import Enum

# region Constants

MAX_TIME_IMMEDIATE = 0  # do not wait
MAX_TIME_INDEFINITE = 0xFFFFFFFF  # wait indefinitely

# endregion
# region Enums


class AmplitudeUnits(Enum):
    """
    Specifies the amplitude units for input, output and display amplitude.
    """
    DBM = 0  # Sets the spectrum analyzer to measure in decibels relative to 1 milliwatt
    DBMV = 1  # Sets the spectrum analyzer to measure in decibels relative to 1 millivolt
    DBUV = 2  # Sets the spectrum analyzer to measure in decibels relative to 1 microvolt
    VOLT = 3  # Sets the spectrum analyzer to measure in volts
    WATT = 4  # Sets the spectrum analyzer to measure in watts


class DetectorType(Enum):
    """
    Specifies detector types.
    """
    AUTO_PEAK = 0  # Allows the detector to capture better readings by using both positive and negative peak values
                   # when noise is present.
    AVERAGE = 1  # Average value of samples taken within the bin for a dedicated point on the display.
    MAXIMUM_PEAK = 2  # Obtains the maximum video signal between the last display point and the present display point.
    MINIMUM_PEAK = 3  # Obtains the minimum video signal between the last display point and the present display point.
    SAMPLE = 4  # Pick one point within a bin.
    RMS = 5  # RMS value of samples taken within the bin for a dedicated point on the display


class TraceType(Enum):
    """
    Specifies trace types.
    """
    CLEAR_WRITE = 0  # Sets the spectrum analyzer to clear previous sweep data off the display before performing a
                     # sweep. Subsequent sweeps may or may not clear the display first, but the data array at the end
                     # of the sweep is entirely new.
    MAXIMUM_HOLD = 1  # Sets the spectrum analyzer to keep the data from either the previous data or the new sweep
                      # data, which ever is higher.
    MINIMUM_HOLD = 2  # Sets the spectrum analyzer to keep the data from either the previous data or the new sweep
                      # data, which ever is lower
    VIDEO_AVERAGE = 3  # Sets the spectrum analyzer to maintain a running average of the swept data.
    VIEW = 4  # Disables acquisition into this trace but displays the existing trace data.
    STORE = 5  # Disables acquisition and disables the display of the existing trace data.


class VerticalScale(Enum):
    """
    Specifies the vertical scale
    """
    LINEAR = 0  # Specifies the vertical scale in linear units.
    LOGARITHMIC = 1  # Specifies the vertical scale in logarithmic units.


class AcquisitionStatus(Enum):
    """
    Specifies acquisitions stati
    """
    COMPLETE = 1  # The spectrum analyzer has completed the acquisition.
    IN_PROGRESS = 0  # The spectrum analyzer is still acquiring data.
    UNKNOWN = 2  # The spectrum analyzer cannot determine the status of the acquisition.


class MarkerSearch(Enum):
    """
    Specifies what signal the marker search should look for.
    """
    HIGHEST = 0  # Sets marker search for the highest amplitude.
    MINIMUM = 1  # Sets marker search for the minimum amplitude.
    NEXT_PEAK = 2  # Sets marker search for the next highest peak.
    NEXT_PEAK_LEFT = 3  # Sets marker search for the next peak left of the marker position.
    NEXT_PEAK_RIGHT = 4  # Sets marker search for the next peak right of the marker position


class TriggerSource(Enum):
    """
    Specifies the source of the trigger signal that causes the analyzer to leave the Wait-For-Trigger state.
    """
    EXTERNAL = 0  # The spectrum analyzer waits until it receives a trigger on the external trigger connector.
    IMMEDIATE = 1  # The spectrum analyzer does not wait for a trigger of any kind.
    SOFTWARE = 2  # The spectrum analyzer waits until the Send Software Trigger function executes. For more information,
                  # refer to Section 2, Software Triggering Capability of the Standard Cross-Class Capabilities
                  # Specification.
    AC_LINE = 3  # The spectrum analyzer waits until it receives a trigger on the AC line.
    VIDEO = 4  # The spectrum analyzer waits until it receives a video level.


class Slope(Enum):
    """
    Specifies the possible slopes for triggers.
    """
    POSITIVE = 0  # Specifies positive slope.
    NEGATIVE = 1  # Specifies negative slope.


class MarkerType(Enum):
    """
    Specifies marker types.
    """
    NORMAL = 0  # Regular marker used to make absolute measurements.
    DELTA = 1   # Marker used in conjunction with the reference marker to make relative measurements.

# endregion
#region Exceptions

class TriggerNotSoftwareException(Exception):
    """
    Raised if trigger source is not set to software trigger.
    """


class MarkerNotEnabledException(Exception):
    """
    Raised if the driver tries to perform an operation on the marker and it is not enabled.
    """


class NotDeltaMarkerException(Exception):
    """
    Raised if the marker type is not delta.

    This exception is used when the driver tries to perform a delta marker operation on the marker, but the marker
    is not a delta marker.
    """


# endregion
# region Basic Interface


class SpecAnIviInterface(metaclass=InterfaceMetaclass):
    """
    Interface for spectrum analyzer driver implementation following the IVI specification.
    """
    class level:
        @property
        @abc.abstractmethod
        def amplitude_units(self):
            """
            Specifies the amplitude units for input, output and display amplitude.
            """
            pass

        @amplitude_units.setter
        def amplitude_units(self, value):
            pass

        @property
        @abc.abstractmethod
        def attenuation(self):
            """
            Specifies the input attenuation (in positive dB).
            """
            pass

        @attenuation.setter
        def attenuation(self, value):
            pass

        @property
        @abc.abstractmethod
        def attenuation_auto(self):
            """
            Selects attenuation automatically.

            If set to True, attenuation is automatically selected. If set to False, attenuation is manually selected.
            """
            pass

        @attenuation_auto.setter
        def attenuation_auto(self, value):
            pass

        @property
        @abc.abstractmethod
        def input_impedance(self):
            """
            Specifies the value of input impedance.

            Specifies the value of input impedance, in ohms, expected at the active input port. This is typically
            50 ohms or 75 ohms.
            """
            pass

        @input_impedance.setter
        def input_impedance(self, value):
            pass

        @property
        @abc.abstractmethod
        def reference(self):
            """
            The calibrated vertical position of the captured data used as a reference for amplitude measurements. This
            is typically set to a value slightly higher than the highest expected signal level. The units are
            determined by the Amplitude Units attribute.
            """
            pass

        @reference.setter
        def reference(self, value):
            pass

        @property
        @abc.abstractmethod
        def reference_offset(self):
            """
            Specifies an offset for the Reference Level attribute.

            This value is used to adjust the reference level for external signal gain or loss. A positive value
            corresponds to a gain while a negative number corresponds to a loss. The value is in dB.
            """
            pass

        @reference_offset.setter
        def reference_offset(self, value):
            pass

        @abc.abstractmethod
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
            pass

    class acquisition:
        @property
        @abc.abstractmethod
        def detector_type(self):
            """
            Specifies the detector type.

            Specifies the detection method used to capture and process the signal. This governs the data acquisition
            for a particular sweep, but does not have any control over how multiple sweeps are processed.
            """
            pass

        @detector_type.setter
        def detector_type(self, value):
            pass

        @property
        @abc.abstractmethod
        def detector_type_auto(self):
            """
            Select detector type automatically.

            If set to True, the detector type is automatically selected. The relationship between Trace Type and
            Detector Type is not defined by the specification when the Detector Type Auto is set to True. If set to
            False, the detector type is manually selected.
            """
            pass

        @detector_type_auto.setter
        def detector_type_auto(self, value):
            pass

        @property
        @abc.abstractmethod
        def number_of_sweeps(self):
            """
            This attribute defines the number of sweeps.

            This attribute value has no effect if the Trace Type attribute is set to the value Clear Write.
            """
            pass

        @number_of_sweeps.setter
        def number_of_sweeps(self, value):
            pass

        @property
        @abc.abstractmethod
        def sweep_mode_continuous(self):
            """
            Is the sweep mode continuous?

            If set to True, the sweep mode is continuous If set to False, the sweep mode is not continuous.
            """
            pass

        @sweep_mode_continuous.setter
        def sweep_mode_continuous(self, value):
            pass

        @property
        @abc.abstractmethod
        def vertical_scale(self):
            """
            Specifies the vertical scale of the measurement hardware (use of log amplifiers versus linear amplifiers).
            """
            pass

        @vertical_scale.setter
        def vertical_scale(self, value):
            pass

        @abc.abstractmethod
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
            pass

    class frequency:
        @property
        @abc.abstractmethod
        def start(self):
            """
            Start frequency.

            Specifies the left edge of the frequency domain in Hertz. This is used in conjunction with the Frequency
            Stop attribute to define the frequency domain. If the Frequency Start attribute value is equal to the
            Frequency Stop attribute value then the spectrum analyzer's horizontal attributes are in time-domain.
            """
            pass

        @start.setter
        def start(self, value):
            pass

        @property
        @abc.abstractmethod
        def stop(self):
            """
            Stop frequency.

            Specifies the right edge of the frequency domain in Hertz. This is used in conjunction with the Frequency
            Start attribute to define the frequency domain. If the Frequency Start attribute value is equal to the
            Frequency Stop attribute value then the spectrum analyzer's horizontal attributes are in time-domain.
            """
            pass

        @stop.setter
        def stop(self, value):
            pass

        @property
        @abc.abstractmethod
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
            pass

        @offset.setter
        def offset(self, value):
            pass

        @abc.abstractmethod
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
            pass

        @abc.abstractmethod
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
            pass


    class sweep_coupling:
        @property
        @abc.abstractmethod
        def resolution_bandwidth(self):
            """
            Specifies the resolution bandwidth.

            Specifies the width of the IF filter in Hertz. For more information see Section 4.1.1, Sweep Coupling
            Overview.
            """
            pass

        @resolution_bandwidth.setter
        def resolution_bandwidth(self, value):
            pass

        @property
        @abc.abstractmethod
        def resolution_bandwidth_auto(self):
            """
            Select resolution bandwidth automatically.

            If set to True, the resolution bandwidth is automatically selected. If set to False, the resolution
            bandwidth is manually selected.
            """
            pass

        @resolution_bandwidth_auto.setter
        def resolution_bandwidth_auto(self, value):
            pass

        @property
        @abc.abstractmethod
        def sweep_time(self):
            """
            Specifies the sweep time.

            Specifies the length of time to sweep from the left edge to the right edge of the current domain.
            The units are seconds.
            """
            pass

        @sweep_time.setter
        def sweep_time(self, value):
            pass

        @property
        @abc.abstractmethod
        def sweep_time_auto(self):
            """
            Select sweep time automatically.

            If set to True, the sweep time is automatically selected If set to False, the sweep time is manually
            selected.
            """
            pass

        @sweep_time_auto.setter
        def sweep_time_auto(self, value):
            pass

        @property
        @abc.abstractmethod
        def video_bandwidth(self):
            """
            Specifies the video bandwidth of the post-detection filter in Hertz.
            """
            pass

        @video_bandwidth.setter
        def video_bandwidth(self, value):
            pass

        @property
        @abc.abstractmethod
        def video_bandwidth_auto(self):
            """
            Select video bandwidth automatically.

            If set to True, the video bandwidth is automatically selected. If set to False, the video bandwidth is
            manually selected.
            """
            pass

        @video_bandwidth_auto.setter
        def video_bandwidth_auto(self, value):
            pass

        @abc.abstractmethod
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
            pass

    class trace:
        """
        Repeated capability, attribute name traces.
        """
        @property
        @abc.abstractmethod
        def name(self):
            """
            Name of trace.

            Returns the physical repeated capability identifier defined by the specific driver for the trace that
            corresponds to the index that the user specifies. If the driver defines a qualified trace name, this
            property returns the qualified name.
            """
            pass

        @property
        @abc.abstractmethod
        def type(self):
            """
            Specifies the representation of the acquired data.
            """
            pass

        @type.setter
        def type(self, value):
            pass

        @abc.abstractmethod
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
            pass

        @abc.abstractmethod
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
                                 otherwise: time the functions waits before raising a timeout error in seconds.
            :return: (numpy array of frequencies, numpy array of amplitude values)
            """
            pass

    class traces(metaclass=abc.ABCMeta):
        @abc.abstractmethod
        def initiate(self):
            """
            This function initiates an acquisition.

            After calling this function, the spectrum analyzer leaves the idle state.

            This function does not check the instrument status. The user calls the Acquisition Status function to
            determine when the acquisition is complete.
            """
            pass

        @abc.abstractmethod
        def abort(self):
            """
            Aborts a running measurement.

            This function aborts a previously initiated measurement and returns the spectrum analyzer to the idle
            state. This function does not check instrument status.
            """
            pass

        @abc.abstractmethod
        def acquisition_status(self):
            """
            This function determines and returns the status of an acquisition.
            """
            pass

# endregion
# region Extensions


class MultitraceExtensionInterface(metaclass=abc.ABCMeta):
    """
    Extension IVI methods for spectrum analyzers supporting simple mathematical operations on traces
    """
    class traces:
        class math(metaclass=abc.ABCMeta):
            """
            The math namespace is supposed to be implemented as traces.math and not as repeated capability.
            """
            @abc.abstractmethod
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
                pass

            @abc.abstractmethod
            def copy(self, dest_trace, src_trace):
                """
                Copies a trace.

                This function copies the data array from one trace into another trace. Any data in the Destination
                Trace is deleted.

                :param dest_trace: Specifies the name of the trace into which the array is copied.
                :param src_trace: Specifies the name of the trace to be copied.
                :return:
                """
                pass

            @abc.abstractmethod
            def exchange(self, trace1, trace2):
                """
                Exchanges two traces.

                This function exchanges the data arrays of two traces.

                :param trace1: Specifies the name of the first trace to be exchanged.
                :param trace2: Specifies the name of the second trace to be exchanged.
                :return:
                """
                pass

            @abc.abstractmethod
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
                pass


class MarkerExtensionInterface(metaclass=abc.ABCMeta):
    """
    The IviSpecAnMarker extension group supports spectrum analyzers that have markers. Markers are applied
    to traces and used for a wide range of operations. Some operations are simple, such as reading an
    amplitude value at an X-axis position, while others operations are complex, such as signal tracking.
    """

    class marker(metaclass=abc.ABCMeta):
        """
        Contains all marker functions. Repeated namespace whose name is markers
        """
        @property
        @abc.abstractmethod
        def amplitude(self):
            """
            Marker amplitude.

            Returns the amplitude of the marker. The units are specified by the Amplitude Units attribute, except
            when the Marker Type attribute is set to Delta. Then the units are dB. If the Marker Enabled attribute is
            set to False, any attempt to read this attribute returns the Marker Not Enabled error.
            :return: Query Marker
            """
            pass

        @property
        @abc.abstractmethod
        def enabled(self):
            """
            Marker enabled.

            If set to True, the  marker is enabled. When False, the marker is disabled.
            """
            pass

        @enabled.setter
        def enabled(self, value):
            pass

        class frequency_counter(metaclass=abc.ABCMeta):
            @property
            @abc.abstractmethod
            def enabled(self):
                """
                Frequency counter enabled.

                Enables/disables the marker frequency counter for greater marker measurement accuracy. If set to True,
                the marker frequency counter is enabled. If set to False, the marker frequency counter is disabled. This
                attribute returns the Marker Not Enabled error if the Marker Enabled attribute is set to False..
                """
                pass

            @enabled.setter
            def enabled(self, value):
                pass

            @property
            @abc.abstractmethod
            def resolution(self):
                """
                Frequency counter resolution.

                Specifies the resolution of the frequency counter in Hertz. The measurement gate time is the reciprocal
                of the specified resolution.
                """
                pass

            @resolution.setter
            def resolution(self, value):
                pass

            @abc.abstractmethod
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

        @property
        @abc.abstractmethod
        def name(self):
            """
            This property returns the marker identifier.
            """
            pass

        @property
        @abc.abstractmethod
        def position(self):
            """
            Marker position.

            Specifies the frequency in Hertz or time position in seconds of the marker (depending on the mode in
            which the analyzer is operating, frequency or time-domain). This attribute returns the Marker Not
            Enabled error if the marker is not enabled.
            """
            pass

        @position.setter
        def position(self, value):
            pass

        @property
        @abc.abstractmethod
        def threshold(self):
            """
            Specifies the lower limit of the search domain vertical range for the Marker Search function.
            """
            pass

        @threshold.setter
        def threshold(self, value):
            pass

        @property
        @abc.abstractmethod
        def trace(self):
            """
            Specifies the Trace for the marker.
            """
            pass

        @trace.setter
        def trace(self, value):
            pass

        @property
        @abc.abstractmethod
        def peak_excursion(self):
            """
            Specifies the minimum amplitude variation of the signal in dB that the Marker Search function can
            identify as a peak.
            """
            pass

        @peak_excursion.setter
        def peak_excursion(self, value):
            pass

        @property
        @abc.abstractmethod
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
            pass

        @signal_track_enabled.setter
        def signal_track_enabled(self, value):
            pass

        @abc.abstractmethod
        def configure_enabled(self, enabled, trace):
            """
            This function enables the marker on the specified Trace.

            :param enabled: Enables or disables the marker. The driver uses this value to set the Marker Enabled
                            attribute. See the attribute description for more details.
            :param trace: Specifies the trace name. The driver uses this value to set the Marker Trace attribute.
                          See the attribute description for more details.
            :return:
            """
            pass

        @abc.abstractmethod
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
            pass

        @abc.abstractmethod
        def search(self, search_type):
            """
            This function specifies the type of marker search and performs the search. This function returns the Marker
            Not Enabled error if the Marker Enabled attribute is set to False.

            :param search_type: Specifies the type of marker search.
            """
            pass

        @abc.abstractmethod
        def query(self):
            """
            This function returns the horizontal position and the amplitude level of the marker.

            :return: set (marker position, marker amplitude)
            """
            pass

    class markers(metaclass=abc.ABCMeta):
        @abc.abstractmethod
        def disable_all(self):
            """
            This function disables all markers.
            """
            pass


class TriggerExtensionInterface(metaclass=abc.ABCMeta):
    """
    This extension group specifies the source of the trigger signal that causes the analyzer to leave the
    Wait-For-Trigger state.
    """
    class trigger:
        @property
        @abc.abstractmethod
        def source(self):
            """
            Specifies the source of the trigger signal that causes the analyzer to leave the Wait-For-Trigger state.
            """
            pass

        @source.setter
        def source(self, value):
            pass


class ExternalTriggerExtensionInterface(metaclass=abc.ABCMeta):
    """
    This extension group specifies the external trigger level and external trigger slope when the Trigger Source
    Attribute is set to external, which causes the analyzer to leave the Wait-For-Trigger state.
    """
    class trigger:
        class external(metaclass=abc.ABCMeta):
            @property
            @abc.abstractmethod
            def level(self):
                """
                Specifies the level, in Volts, that the external trigger signal shall reach to trigger the acquisition.
                """
                pass

            @level.setter
            def level(self, value):
                pass

            @property
            @abc.abstractmethod
            def slope(self):
                """
                Specifies which slope of the external trigger signal triggers the acquisition.

                See also: Slope.
                """
                pass

            @slope.setter
            def slope(self, value):
                pass

            @abc.abstractmethod
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
                pass


class SoftwareTriggerExtensionInterface(metaclass=abc.ABCMeta):
    """
    The IviSpecAnSoftwareTrigger Extension Group supports spectrum analyzers that can acquire traces based
    on a software trigger signal. The user can send a software trigger to cause signal output to occur.

    This extension affects instrument behavior when the Trigger Source attribute is set to Software.
    """
    @abc.abstractmethod
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
        pass


class VideoTriggerExtensionInterface(metaclass=abc.ABCMeta):
    """
    This extension group specifies the video trigger level and video trigger slope when the Trigger Source
    attribute is set to Video, which causes the analyzer to leave the Wait-For-Trigger state.
    """
    class trigger:
        class video(metaclass=abc.ABCMeta):
            @property
            @abc.abstractmethod
            def level(self):
                """
                Specifies the level that the video signal shall reach to trigger the acquisition.

                The units are specified by the Amplitude Units attribute.
                """
                pass

            @level.setter
            def level(self, value):
                pass

            @property
            @abc.abstractmethod
            def slope(self):
                """
                Specifies which slope of the video signal triggers the acquisition.

                Possible values: Slope Enum.
                """
                pass

            @slope.setter
            def slope(self, value):
                pass

            @abc.abstractmethod
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
                pass


class DisplayExtensionInterface(metaclass=abc.ABCMeta):
    """
    The IviSpecAnDisplay extension group controls the display related attributes.
    """
    class display(metaclass=abc.ABCMeta):
        @property
        @abc.abstractmethod
        def number_of_divisions(self):
            """
            Specifies the number of vertical screen divisions.
            """
            pass

        @property
        @abc.abstractmethod
        def units_per_division(self):
            """
            Specifies the number of vertical units in one screen division.

            This attribute is typically used in conjunction with the Reference Level attribute to set the vertical
            range of the spectrum analyzer.
            """
            pass

        @units_per_division.setter
        def units_per_division(self, value):
            pass


class MarkerTypeExtensionInterface(metaclass=abc.ABCMeta):
    """
    The IviSpecAnMarkerType extension group provides support for analyzers that have multiple marker types.
    """
    class marker(metaclass=abc.ABCMeta):
        @property
        @abc.abstractmethod
        def type(self):
            """
            Specifies the marker type of the marker.

            See also: MarkerType
            """
            pass


class DeltaMarkerExtensionInterface(metaclass=abc.ABCMeta):
    """
    The IviSpecAnDeltaMarker extension group provides delta-marker capabilities.

    This section supports analyzers that have delta-marker capabilities. A delta marker has the same properties
    as a normal marker except that its position and amplitude are relative to a fixed reference point. This
    reference point is defined when the marker is converted from a normal marker to a delta marker.
    """
    class marker(metaclass=abc.ABCMeta):
        @property
        @abc.abstractmethod
        def reference_amplitude(self):
            """
            Amplitude of the reference marker.

            Specifies the reference marker amplitude when the active marker is a delta marker. The unit is given by the
            Amplitude Units attribute.

            If the Marker Type attribute is not Delta, this property raises the NotDeltaMarkerException.
            """
            pass

        @property
        @abc.abstractmethod
        def reference_position(self):
            """
            Position of the reference marker.

            Specifies the position of the reference marker, when the active marker is a delta marker. The units are
            Hertz for frequency domain measurements, and seconds for time domain measurements.

            If the Marker Type attribute is not Delta, this property raises the NotDeltaMarkerException.
            """
            pass

        @abc.abstractmethod
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
            pass

        @property
        @abc.abstractmethod
        def query_reference(self):
            """
            This function returns the amplitude and position of the reference marker. If the Marker Type attribute is
            not Delta, this function returns the Not Delta Marker error.

            :return: set of reference position and amplitude
            """
            pass


class ExternalMixerExtensionInterface(metaclass=abc.ABCMeta):
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
    class external_mixer(metaclass=abc.ABCMeta):
        @property
        @abc.abstractmethod
        def enabled(self):
            """
            Enables external mixer.

            If set to True, the external mixer is enabled. If set to False, the external mixer is disabled.
            """
            pass

        @enabled.setter
        def enabled(self, value):
            pass

        @property
        @abc.abstractmethod
        def average_conversion_loss(self):
            """
            Specifies the average conversion loss.
            """
            pass

        @average_conversion_loss.setter
        def average_conversion_loss(self, value):
            pass

        @property
        @abc.abstractmethod
        def harmonic(self):
            """
            Specifies the order n of the harmonic used for conversion.
            """
            pass

        @harmonic.setter
        def harmonic(self, value):
            pass

        @property
        @abc.abstractmethod
        def number_of_ports(self):
            """
            Specifies the number of mixer ports.
            """
            pass

        @number_of_ports.setter
        def number_of_ports(self, value):
            pass

        @abc.abstractmethod
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
            pass

        class bias(metaclass=abc.ABCMeta):
            @property
            @abc.abstractmethod
            def level(self):
                """
                Specifies the bias current in Amps.
                """
                pass

            @level.setter
            def level(self, value):
                pass

            @property
            @abc.abstractmethod
            def enabled(self):
                """
                Bias enabled.

                If set to True, the external mixer bias is enabled. If set to False, the external mixer bias
                is disabled.
                """
                pass

            @enabled.setter
            def enabled(self, value):
                pass

            @property
            @abc.abstractmethod
            def limit(self):
                """
                Bias current limit.

                Specifies the bias current limit in Amps.
                """
                pass

            @limit.setter
            def limit(self, value):
                pass

            @abc.abstractmethod
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
                pass

        class conversion_loss_table(metaclass=abc.ABCMeta):
            @property
            @abc.abstractmethod
            def enabled(self):
                """
                Conversion loss table enabled.

                If set to True, the conversion loss table is enabled. If set to False, the conversion loss table is
                disabled.
                """
                pass

            @enabled.setter
            def enabled(self, value):
                pass

            @abc.abstractmethod
            def configure(self, frequency, conversion_loss):
                """
                Configures conversion loss table.

                This function configures the conversion loss table by specifying a series of frequency and a power loss
                pairs.

                :param frequency: array. Specifies the frequency values for the pairs.
                :param conversion_loss: array. Specifies the conversion loss values for the pairs.
                :return:
                """
                pass


class PreselectorExtensionInterface(metaclass=abc.ABCMeta):
    """
    The IviSpecAnPreselector extension controls preselectors.

    Preselectors are a network of filters and preamplifiers that are built into one unit for reducing noise and
    increasing dynamic range of an analyzer.  Preselectors are often separate instruments, but they are instruments that
    only work with spectrum analyzers. Some analyzers have internal preselectors.
    """
    class preselector(metaclass=abc.ABCMeta):
        @abc.abstractmethod
        def peak(self):
            """
            Adjusts the preselector.

            This function adjusts the preselector to obtain the maximum readings for the current start and stop
            frequency. This function may affect the marker configuration.
            """
            pass

# endregion
