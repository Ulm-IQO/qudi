from interface import scope
from .python_ivi_base import PythonIviBase

import inspect
from qtpy.QtCore import QObject
from qtpy.QtCore import Signal
import ivi.scope


class Acquisition(QObject, scope.AcquisitionInterface):
    """
    The acquisition sub-system configures the acquisition type, the size of the waveform record,
    the length of time that corresponds to the overall waveform record, and the position of the
    first point in the waveform record relative to the Trigger Event.
    """

    start_time_changed = Signal(float)
    type_changed = Signal(str)
    number_of_points_minimum_changed = Signal(int)
    time_per_record_changed = Signal(float)

    @property
    def start_time(self):
        return self.parent().driver.acquisition.start_time

    @start_time.setter
    def start_time(self, value):
        self.parent().driver.acquisition.start_time = value
        self.start_time_changed.emit(value)

    @property
    def type(self):
        return self.parent().driver.acquisition.type

    @type.setter
    def type(self, value):
        self.parent().driver.acquisition.type = value
        self.type_changed.emit(value)

    @property
    def number_of_points_minimum(self):
        return self.parent().driver.acquisition.number_of_points_minimum

    @number_of_points_minimum.setter
    def number_of_points_minimum(self, value):
        self.parent().driver.acquisition.number_of_points_minimum = value
        self.number_of_points_minimum_changed.emit(value)

    @property
    def record_length(self):
        return self.parent().driver.acquisition.record_length

    @property
    def sample_rate(self):
        return self.parent().driver.acquisition.sample_rate

    @property
    def time_per_record(self):
        return self.parent().driver.acquisition.time_per_record

    @time_per_record.setter
    def time_per_record(self, value):
        self.parent().driver.acquisition.time_per_record = value
        self.time_per_record_changed.emit(value)

    def configure_record(self, time_per_record, minimum_number_of_points, acquisition_start_time):
        self.parent().driver.acquisition.configure_record(time_per_record,
                                                          minimum_number_of_points,
                                                          acquisition_start_time)
        self.time_per_record_changed.emit(time_per_record)
        self.number_of_points_minimum_changed.emit(minimum_number_of_points)
        self.start_time_changed.emit(acquisition_start_time)


class Channel(QObject, scope.ChannelInterface):
    enabled_changed = Signal(bool)
    input_impedance_changed = Signal(int)
    input_frequency_max_changed = Signal(float)
    probe_attenuation_changed = Signal(float)
    coupling_changed = Signal(str)
    offset_changed = Signal(float)
    range_changed = Signal(float)

    def __init__(self, channel_index, channel_measurement, **kwargs):
        super().__init__(**kwargs)
        self._channel_index = channel_index
        self._measurement = channel_measurement

    @property
    def name(self):
        """
        This attribute returns the repeated capability identifier defined by
        specific driver for the channel that corresponds to the index that the
        user specifies. If the driver defines a qualified channel name, this
        property returns the qualified name.

        If the value that the user passes for the Index parameter is less than
        zero or greater than the value of the channel count, the attribute raises
        a SelectorRangeException.
        """
        return self.parent().driver.channels[self._channel_index].name

    @property
    def enabled(self):
        """
        If set to True, the oscilloscope acquires a waveform for the channel. If
        set to False, the oscilloscope does not acquire a waveform for the
        channel.
        """
        return self.parent().driver.channels[self._channel_index].enabled

    @enabled.setter
    def enabled(self, value):
        self.parent().driver.channels[self._channel_index].enabled = value
        self.enabled_changed.emit(value)

    @property
    def input_impedance(self):
        """
        Specifies the input impedance for the channel in Ohms.

        Common values are 50.0, 75.0, and 1,000,000.0.
        """
        return self.parent().driver.channels[self._channel_index].input_impedance

    @input_impedance.setter
    def input_impedance(self, value):
        self.parent().driver.channels[self._channel_index].input_impedance = value
        self.input_impedance_changed.emit(value)

    @property
    def input_frequency_max(self):
        """
        Specifies the maximum frequency for the input signal you want the
        instrument to accommodate without attenuating it by more than 3dB. If the
        bandwidth limit frequency of the instrument is greater than this maximum
        frequency, the driver enables the bandwidth limit. This attenuates the
        input signal by at least 3dB at frequencies greater than the bandwidth
        limit.
        """
        return self.parent().driver.channels[self._channel_index].input_frequency_max

    @input_frequency_max.setter
    def input_frequency_max(self, value):
        self.parent().driver.channels[self._channel_index].input_frequency_max = value
        self.input_frequency_max_changed.emit(value)

    @property
    def probe_attenuation(self):
        """
        Specifies the scaling factor by which the probe the end-user attaches to
        the channel attenuates the input. For example, for a 10:1 probe, the
        end-user sets this attribute to 10.0.

        Note that if the probe is changed to one with a different attenuation, and
        this attribute is not set, the amplitude calculations will be incorrect.

        Querying this value will return the probe attenuation corresponding to the
        instrument's actual probe attenuation. Setting this property sets Probe
        Attenuation Auto to False Negative values are not valid.
        """
        return self.parent().driver.channels[self._channel_index].probe_attenuation

    @probe_attenuation.setter
    def probe_attenuation(self, value):
        self.parent().driver.channels[self._channel_index].probe_attenuation = value
        self.probe_attenuation_changed.emit(value)

    @property
    def coupling(self):
        """
        Specifies how the oscilloscope couples the input signal for the channel.

        Values:

        * 'ac'
        * 'dc'
        * 'gnd'
        """
        return self.parent().driver.channels[self._channel_index].coupling

    @coupling.setter
    def coupling(self, value):
        self.parent().driver.channels[self._channel_index].coupling = value
        self.coupling_changed.emit(value)

    @property
    def offset(self):
        """
        Specifies the location of the center of the range that the Vertical Range
        attribute specifies. The value is with respect to ground and is in volts.

        For example, to acquire a sine wave that spans between on 0.0 and 10.0
        volts, set this attribute to 5.0 volts.
        """
        return self.parent().driver.channels[self._channel_index].offset

    @offset.setter
    def offset(self, value):
        self.parent().driver.channels[self._channel_index].offset = value
        self.offset_changed.emit(value)

    @property
    def range(self):
        """
        Specifies the absolute value of the full-scale input range for a channel.
        The units are volts.

        For example, to acquire a sine wave that spans between -5.0 and 5.0 volts,
        set the Vertical Range attribute to 10.0 volts.
        """
        return self.parent().driver.channels[self._channel_index].range

    @range.setter
    def range(self, value):
        self.parent().driver.channels[self._channel_index].range = value
        self.range_changed.emit(value)

    def configure(self, vertical_range, offset, coupling, probe_attenuation, enabled):
        """
        This function configures the most commonly configured attributes of the
        oscilloscope channel sub-system. These attributes are the range, offset,
        coupling, probe attenuation, and whether the channel is enabled.
        """
        self.parent().driver.channels[self._channel_index].configure(
            vertical_range, offset, coupling, probe_attenuation, enabled)

    def configure_characteristics(self, input_impedance, input_frequency_max):
        """
        This function configures the attributes that control the electrical
        characteristics of the channel. These attributes are the input impedance
        and the maximum frequency of the input signal.
        """
        self.parent().driver.channels[self._channel_index].configure_characteristics(
            input_impedance, input_frequency_max)

    @property
    def measurement(self):
        return self._measurement


class Measurement(QObject, scope.MeasurementInterface):
    """
    IVI Methods for Measurement
    """
    @property
    def status(self):
        """
        Acquisition status indicates whether an acquisition is in progress,
        complete, or if the status is unknown.

        Acquisition status is not the same as instrument status, and does not
        necessarily check for instrument errors. To make sure that the instrument
        is checked for errors after getting the acquisition status, call the Error
        Query method. (Note that the end user may want to call Error Query at the
        end of a sequence of other calls which include getting the acquisition
        status - it does not necessarily need to be called immediately.)

        If the driver cannot determine whether the acquisition is complete or not,
        it returns the Acquisition Status Unknown value.

        Values:
        * 'compete'
        * 'in_progress'
        * 'unknown'
        """
        return self.parent().driver.measurement.status

    def abort(self):
        """
        This function aborts an acquisition and returns the oscilloscope to the
        Idle state. This function does not check the instrument status.

        Typically, the end-user calls this function only in a sequence of calls to
        other low-level driver functions. The sequence performs one operation. The
        end-user uses the low-level functions to optimize one or more aspects of
        interaction with the instrument. Call the Error Query function at the
        conclusion of the sequence to check the instrument status.

        If the instrument cannot abort an initiated acquisition, the driver shall
        return the Function Not Supported error.
        """
        self.parent().driver.measurement.abort()

    def initiate(self):
        """
        This function initiates a waveform acquisition. After calling this
        function, the oscilloscope leaves the idle state and waits for a trigger.
        The oscilloscope acquires a waveform for each channel the end-user has
        enabled with the Configure Channel function.

        This function does not check the instrument status. Typically, the
        end-user calls this function only in a sequence of calls to other
        low-level driver functions. The sequence performs one operation. The
        end-user uses the low-level functions to optimize one or more aspects of
        interaction with the instrument. Call the Error Query function at the
        conclusion of the sequence to check the instrument status.
        """
        return self.parent().driver.measurement.initiate()


class ChannelMeasurement(QObject, scope.ChannelMeasurementInterface):
    def __init__(self, channel_index, **kwargs):
        self._channel_index = channel_index
        super().__init__(**kwargs)

    def fetch_waveform(self):
        """
        This function returns the waveform the oscilloscope acquires for the
        specified channel. The waveform is from a previously initiated
        acquisition.

        You use the Initiate Acquisition function to start an acquisition on the
        channels that the end-user configures with the Configure Channel function.
        The oscilloscope acquires waveforms on the concurrently enabled channels.
        If the channel is not enabled for the acquisition, this function returns
        the Channel Not Enabled error.

        Use this function only when the acquisition mode is Normal, Hi Res, or
        Average. If the acquisition type is not one of the listed types, the
        function returns the Invalid Acquisition Type error.

        You use the Acquisition Status function to determine when the acquisition
        is complete. You must call this function separately for each enabled
        channel to obtain the waveforms.

        You can call the Read Waveform function instead of the Initiate
        Acquisition function. The Read Waveform function starts an acquisition on
        all enabled channels, waits for the acquisition to complete, and returns
        the waveform for the specified channel. You call this function to obtain
        the waveforms for each of the remaining channels.

        The return value is a list of (x, y) tuples that represent the time and
        voltage of each data point.  The y point may be NaN in the case that the
        oscilloscope could not sample the voltage.

        The end-user configures the interpolation method the oscilloscope uses
        with the Acquisition.Interpolation property. If interpolation is disabled,
        the oscilloscope does not interpolate points in the waveform. If the
        oscilloscope cannot sample a value for a point in the waveform, the driver
        sets the corresponding element in the waveformArray to an IEEE-defined NaN
        (Not a Number) value. Check for this value with math.isnan() or
        numpy.isnan().

        This function does not check the instrument status. Typically, the
        end-user calls this function only in a sequence of calls to other
        low-level driver functions. The sequence performs one operation. The
        end-user uses the low-level functions to optimize one or more aspects of
        interaction with the instrument. Call the Error Query function at the
        conclusion of the sequence to check the instrument status.
        """
        return self.parent().driver.channels[self._channel_index].measurement.fetch_waveform()

    def read_waveform(self):
        """
        This function initiates an acquisition on the channels that the end-user
        configures with the Configure Channel function. If the channel is not
        enabled for the acquisition, this function returns Channel Not Enabled
        error. It then waits for the acquisition to complete, and returns the
        waveform for the channel the end-user specifies. If the oscilloscope did
        not complete the acquisition within the time period the user specified
        with the max_time parameter, the function returns the Max Time Exceeded
        error.

        Use this function only when the acquisition mode is Normal, Hi Res, or
        Average. If the acquisition type is not one of the listed types, the
        function returns the Invalid Acquisition Type error.

        You call the Fetch Waveform function to obtain the waveforms for each of
        the remaining enabled channels without initiating another acquisition.
        After this function executes, each element in the WaveformArray parameter
        is either a voltage or a value indicating that the oscilloscope could not
        sample a voltage.


        The end-user configures the interpolation method the oscilloscope uses
        with the Acquisition.Interpolation property. If interpolation is disabled,
        the oscilloscope does not interpolate points in the waveform. If the
        oscilloscope cannot sample a value for a point in the waveform, the driver
        sets the corresponding element in the waveformArray to an IEEE-defined NaN
        (Not a Number) value. Check for this value with math.isnan() or
        numpy.isnan(). Check an entire array with

        any(any(math.isnan(b) for b in a) for a in waveform)
        """
        return self.parent().driver.channels[self._channel_index].measurement.read_waveform()


class Trigger(QObject, scope.TriggerInterface):
    """
    IVI Methods for Trigger
    """
    coupling_changed = Signal(str)
    holdoff_changed = Signal(float)
    level_changed = Signal(float)
    source_changed = Signal(str)
    type_changed = Signal(str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._edge = EdgeTrigger(parent=self)
        # go through all trigger extensions the driver supports and add the corresponding implementation
        TriggerInterfaceMap = {
            ivi.scope.TVTrigger: (TVTrigger, 'tv'),
            ivi.scope.RuntTrigger: (RuntTrigger, 'runt'),
            ivi.scope.GlitchTrigger: (GlitchTrigger, 'glitch'),
            ivi.scope.WidthTrigger: (WidthTrigger, 'width'),
            ivi.scope.AcLineTrigger: (AcLineTrigger, 'ac_line')
        }
        for TriggerInterface, item in TriggerInterfaceMap.items():
            if (isinstance(self.parent().driver, TriggerInterface)):
                setattr(self, item[1], item[0]())

    @property
    def coupling(self):
        """
        Specifies how the oscilloscope couples the trigger source.

        Values:

        * 'ac'
        * 'dc'
        * 'lf_reject'
        * 'hf_reject'
        * 'noise_reject'
        """
        return self.parent().driver.trigger.coupling

    @coupling.setter
    def coupling(self, value):
        self.parent().driver.trigger.coupling = value
        self.coupling_changed.emit(value)

    @property
    def holdoff(self):
        """
        Specifies the length of time the oscilloscope waits after it detects a
        trigger until the oscilloscope enables the trigger subsystem to detect
        another trigger. The units are seconds. The Trigger Holdoff attribute
        affects instrument operation only when the oscilloscope requires multiple
        acquisitions to build a complete waveform. The oscilloscope requires
        multiple waveform acquisitions when it uses equivalent-time sampling or
        when the Acquisition Type attribute is set to Envelope or Average.

        Note: Many scopes have a small, non-zero value as the minimum value for
        this attribute. To configure the instrument to use the shortest trigger
        hold-off, the user can specify a value of zero for this attribute.

        Therefore, the IVI Class-Compliant specific driver shall coerce any value
        between zero and the minimum value to the minimum value. No other coercion
        is allowed on this attribute.
        """
        return self.parent().driver.trigger.holdoff

    @holdoff.setter
    def holdoff(self, value):
        self.parent().driver.trigger.holdoff = value
        self.holdoff_changed.emit(value)

    @property
    def level(self):
        """
        Specifies the voltage threshold for the trigger sub-system. The units are
        volts. This attribute affects instrument behavior only when the Trigger
        Type is set to one of the following values: Edge Trigger, Glitch Trigger,
        or Width Trigger.

        This attribute, along with the Trigger Slope, Trigger Source, and Trigger
        Coupling attributes, defines the trigger event when the Trigger Type is
        set to Edge Trigger.
        """
        return self.parent().driver.trigger.level

    @level.setter
    def level(self, value):
        self.parent().driver.trigger.level = value
        self.level_changed.emit(value)

    @property
    def edge(self):
        return self._edge

    @property
    def source(self):
        """
        Specifies the source the oscilloscope monitors for the trigger event. The
        value can be a channel name alias, a driver-specific channel string, or
        one of the values below.

        This attribute affects the instrument operation only when the Trigger Type
        is set to one of the following values: Edge Trigger, TV Trigger, Runt
        Trigger, Glitch Trigger, or Width Trigger.
        """
        return self.parent().driver.trigger.source

    @source.setter
    def source(self, value):
        self.parent().driver.trigger.source = value
        self.source_changed.emit(self.parent().driver.trigger.source)

    @property
    def type(self):
        """
        Specifies the event that triggers the oscilloscope.

        Values:

        * 'edge'
        * 'tv'
        * 'runt'
        * 'glitch'
        * 'width'
        * 'immediate'
        * 'ac_line'
        """
        return self.parent().driver.trigger.type

    @type.setter
    def type(self, value):
        self.parent().driver.trigger.type = value
        self.type_changed.emit(value)

    def configure(self, trigger_type, holdoff):
        """
        This function configures the common attributes of the trigger subsystem.
        These attributes are the trigger type and trigger holdoff.

        When the end-user calls Read Waveform, Read Waveform Measurement, Read Min
        Max Waveform, or Initiate Acquisition, the oscilloscope waits for a
        trigger. The end-user specifies the type of trigger for which the
        oscilloscope waits with the TriggerType parameter.

        If the oscilloscope requires multiple waveform acquisitions to build a
        complete waveform, it waits for the length of time the end-user specifies
        with the Holdoff parameter to elapse since the previous trigger. The
        oscilloscope then waits for the next trigger. Once the oscilloscope
        acquires a complete waveform, it returns to the idle state.
        """
        self.parent().driver.trigger.configure(trigger_type, holdoff)


class EdgeTrigger(QObject, scope.EdgeTriggerInterface):
    """
    IVI methods for Edge triggering
    """
    slope_changed = Signal(str)

    @property
    def slope(self):
        """
        Specifies whether a rising or a falling edge triggers the oscilloscope.

        This attribute affects instrument operation only when the Trigger Type
        attribute is set to Edge Trigger.

        Values:
         * 'positive'
         * 'negative'
        """
        return self.parent().parent().driver.trigger.edge.slope

    @slope.setter
    def slope(self, value):
        self.parent().parent().driver.trigger.slope = value
        self.slope_changed.emit(value)

    def configure(self, source, level, slope):
        """
        This function sets the edge triggering attributes. An edge trigger occurs
        when the trigger signal that the end-user specifies with the Source
        parameter passes through the voltage threshold that the end-user
        specifies with the level parameter and has the slope that the end-user
        specifies with the Slope parameter.

        This function affects instrument behavior only if the Trigger Type is Edge
        Trigger. Set the Trigger Type and Trigger Coupling before calling this
        function.

        If the trigger source is one of the analog input channels, an application
        program should configure the vertical range, vertical offset, vertical
        coupling, probe attenuation, and the maximum input frequency before
        calling this function.
        """
        return self.parent().parent().driver.trigger.edge.configure(source, level, slope)


# ************************ EXTENSIONS **************************************************************


class InterpolationAcquisitionMixin(scope.InterpolationAcquisitionInterface):
    interpolation_changed = Signal(str)

    @property
    def interpolation(self):
        """
        Specifies the interpolation method the oscilloscope uses when it cannot
        resolve a voltage for every point in the waveform record.

        Values:
        * 'none'
        * 'sinex'
        * 'linear'
        """
        return self.parent().driver.acquisition.interpolation

    @interpolation.setter
    def interpolation(self, value):
        self.parent().driver.acquisition.interpolation = value
        self.interpolation_changed.emit(value)


class TVTrigger(QObject, scope.TVTriggerInterface):
    """
    Extension IVI methods for oscilloscopes supporting TV triggering
    """
    trigger_event_changed = Signal(str)
    line_number_changed = Signal(int)
    polarity_changed = Signal(str)
    signal_format_changed = Signal(str)

    @property
    def trigger_event(self):
        """
        Specifies the event on which the oscilloscope triggers.

        Values:
        * 'field1'
        * 'field2'
        * 'any_field'
        * 'any_line'
        * 'line_number'
        """
        return self.parent().driver.trigger.tv.trigger_event

    @trigger_event.setter
    def trigger_event(self, value):
        self.parent().driver.trigger.tv.trigger_event = value
        self.trigger_event_changed.emit(self.parent().driver.trigger.tv.trigger_event)

    @property
    def line_number(self):
        """
        Specifies the line on which the oscilloscope triggers. The driver uses
        this attribute when the TV Trigger Event is set to TV Event Line Number.
        The line number setting is independent of the field. This means that to
        trigger on the first line of the second field, the user must configure
        the line number to the value of 263 (if we presume that field one had 262
        lines).
        """
        return self.parent().driver.trigger.tv.line_number

    @line_number.setter
    def line_number(self, value):
        self.parent().driver.trigger.tv.line_number = value
        self.line_number_changed.emit(self.parent().driver.trigger.tv.line_number)

    @property
    def polarity(self):
        """
        Specifies the polarity of the TV signal.

        Values:
        * 'positive'
        * 'negative'
        """
        return self.parent().driver.trigger.tv.polarity

    @polarity.setter
    def polarity(self, value):
        self.parent().driver.trigger.tv.polarity = value
        self.polarity_changed.emit(self.parent().driver.trigger.tv.polarity)

    @property
    def signal_format(self):
        """
        Specifies the format of TV signal on which the oscilloscope triggers.

        Values:
        * 'ntsc'
        * 'pal'
        * 'secam'
        """
        return self.parent().driver.trigger.tv.signal_format

    @signal_format.setter
    def signal_format(self, value):
        self.parent().driver.trigger.tv.signal_format = value
        self.signal_format_changed.emit(self.parent().driver.trigger.tv.signal_format)

    def configure(self, source, signal_format, event, polarity):
        """
        This function configures the oscilloscope for TV triggering. It configures
        the TV signal format, the event and the signal polarity.

        This function affects instrument behavior only if the trigger type is TV
        Trigger. Set the Trigger Type and Trigger Coupling before calling this
        function.
        """
        self.parent().driver.trigger.tv.configure(source, signal_format, event, polarity)


class RuntTrigger(QObject, scope.RuntTriggerInterface):
    """
    Extension IVI methods for oscilloscopes supporting runt triggering
    """
    threshold_high_changed = Signal(float)
    threshold_low_changed = Signal(float)
    polarity_changed = Signal(str)

    @property
    def threshold_high(self):
        """
        Specifies the high threshold the oscilloscope uses for runt triggering.
        The units are volts.
        """
        return self.parent().driver.trigger.runt.threshold_high

    @threshold_high.setter
    def threshold_high(self, value):
        self.parent().driver.trigger.runt.threshold_high = value
        self.threshold_high_changed.emit(self.parent().driver.trigger.runt.threshold_high)

    @property
    def threshold_low(self):
        """
        Specifies the low threshold the oscilloscope uses for runt triggering.
        The units are volts.
        """
        return self.parent().driver.trigger.runt.threshold_low

    @threshold_low.setter
    def threshold_low(self, value):
        self.parent().driver.trigger.runt.threshold_low = value
        self.threshold_low_changed.emit(self.parent().driver.trigger.runt.threshold_low)

    @property
    def polarity(self):
        """
        Specifies the polarity of the runt that triggers the oscilloscope.

        Values:
        * 'positive'
        * 'negative'
        * 'either'
        """
        return self.parent().driver.trigger.runt.polarity

    @polarity.setter
    def polarity(self, value):
        self.parent().driver.trigger.runt.polarity = value
        self.polarity_changed.emit(self.parent().driver.trigger.runt.polarity)

    def configure(self, source, threshold_low, threshold_high, polarity):
        """
        This function configures the runt trigger. A runt trigger occurs when the
        trigger signal crosses one of the runt thresholds twice without crossing
        the other runt threshold. The end-user specifies the runt thresholds with
        the RuntLowThreshold and RuntHighThreshold parameters. The end-user
        specifies the polarity of the runt with the RuntPolarity parameter.

        This function affects instrument behavior only if the trigger type is Runt
        Trigger. Set the trigger type and trigger coupling before calling this
        function.
        """
        self.parent().driver.trigger.runt.configure(source, threshold_low, threshold_high, polarity)


class WidthTrigger(QObject, scope.WidthTriggerInterface):
    """
    Extension IVI methods for oscilloscopes supporting width triggering
    """
    condition_changed = Signal(str)
    threshold_high_changed = Signal(float)
    threshold_low_changed = Signal(float)
    polarity_changed = Signal(str)

    @property
    def condition(self):
        """
        Specifies whether a pulse that is within or outside the high and low
        thresholds triggers the oscilloscope. The end-user specifies the high and
        low thresholds with the Width High Threshold and Width Low Threshold
        attributes.

        Values:
        * 'within'
        * 'outside'
        """
        return self.parent().driver.trigger.width.condition

    @condition.setter
    def condition(self, value):
        self.parent().driver.trigger.width.condition = value
        self.condition_changed.emit(self.parent().driver.trigger.width.condition)

    @property
    def threshold_high(self):
        """
        Specifies the high width threshold time. Units are seconds.
        """
        return self.parent().driver.trigger.width.threshold_high

    @threshold_high.setter
    def threshold_high(self, value):
        self.parent().driver.trigger.width.threshold_high = value
        self.threshold_high_changed.emit(self.parent().driver.trigger.width.threshold_high)

    @property
    def threshold_low(self):
        """
        Specifies the low width threshold time. Units are seconds.
        """
        return self.parent().driver.trigger.width.threshold_low

    @threshold_low.setter
    def threshold_low(self, value):
        self.parent().driver.trigger.width.threshold_low = value
        self.threshold_low_changed.emit(self.parent().driver.trigger.width.threshold_low)

    @property
    def polarity(self):
        """
        Specifies the polarity of the pulse that triggers the oscilloscope.

        Values:
        * 'positive'
        * 'negative'
        * 'either'
        """
        return self.parent().driver.trigger.width.polarity

    @polarity.setter
    def polarity(self, value):
        self.parent().driver.trigger.width.polarity = value
        self.polarity_changed.emit(self.parent().driver.trigger.width.polarity)

    def configure(self, source, level, threshold_low, threshold_high, polarity, condition):
        """
        This function configures the width trigger. A width trigger occurs when
        the oscilloscope detects a positive or negative pulse with a width
        between, or optionally outside, the width thresholds. The end-user
        specifies the width thresholds with the WidthLowThreshold and
        WidthHighThreshold parameters. The end-user specifies whether the
        oscilloscope triggers on pulse widths that are within or outside the width
        thresholds with the WidthCondition parameter. The end-user specifies the
        polarity of the pulse with the WidthPolarity parameter. The trigger does
        not actually occur until the edge of a pulse that corresponds to the
        WidthLowThreshold, WidthHighThreshold, WidthCondition, and WidthPolarity
        crosses the threshold the end-user specifies with the TriggerLevel
        parameter.

        This function affects instrument behavior only if the trigger type is
        Width Trigger. Set the trigger type and trigger coupling before calling
        this function.
        """
        self.parent().driver.trigger.width.configure(source, level, threshold_low, threshold_high, polarity, condition)


class GlitchTrigger(QObject, scope.GlitchTriggerInterface):
    """
    Extension IVI methods for oscilloscopes supporting glitch triggering
    """
    condition_changed = Signal(str)
    polarity_changed = Signal(str)
    width_changed = Signal(float)

    @property
    def condition(self):
        """
        Specifies the glitch condition. This attribute determines whether the
        glitch trigger happens when the oscilloscope detects a pulse with a
        width less than or greater than the width value.

        Values:
        * 'greater_than'
        * 'less_than'
        """
        return self.parent().driver.trigger.glitch.condition

    @condition.setter
    def condition(self, value):
        self.parent().driver.trigger.glitch.condition = value
        self.condition_changed.emit(self.parent().driver.trigger.glitch.condition)

    @property
    def polarity(self):
        """
        Specifies the polarity of the glitch that triggers the oscilloscope.

        Values:
        * 'positive'
        * 'negative'
        * 'either'
        """
        return self.parent().driver.trigger.glitch.polarity

    @polarity.setter
    def polarity(self, value):
        self.parent().driver.trigger.glitch.polarity = value
        self.polarity_changed.emit(self.parent().driver.trigger.glitch.polarity)

    @property
    def width(self):
        """
        Specifies the glitch width. The units are seconds. The oscilloscope
        triggers when it detects a pulse with a width less than or greater than
        this value, depending on the Glitch Condition attribute.
        """
        return self.parent().driver.trigger.glitch.width

    @width.setter
    def width(self, value):
        self.parent().driver.trigger.glitch.width = value
        self.condition_changed.emit(self.parent().driver.trigger.glitch.width)

    def configure(self, source, level, width, polarity, condition):
        """
        This function configures the glitch trigger. A glitch trigger occurs when
        the trigger signal has a pulse with a width that is less than or greater
        than the glitch width. The end user specifies which comparison criterion
        to use with the GlitchCondition parameter. The end-user specifies the
        glitch width with the GlitchWidth parameter. The end-user specifies the
        polarity of the pulse with the GlitchPolarity parameter. The trigger does
        not actually occur until the edge of a pulse that corresponds to the
        GlitchWidth and GlitchPolarity crosses the threshold the end-user
        specifies in the TriggerLevel parameter.

        This function affects instrument behavior only if the trigger type is
        Glitch Trigger. Set the trigger type and trigger coupling before calling
        this function.
        """
        self.parent().driver.trigger.glitch.configure(source, level, width, polarity, condition)


class AcLineTrigger(QObject, scope.AcLineTriggerInterface):
    """
    Extension IVI methods for oscilloscopes supporting AC line triggering
    """
    slope_changed = Signal(str)

    @property
    def slope(self):
        """
        Specifies the slope of the zero crossing upon which the scope triggers.

        Values:
        * 'positive'
        * 'negative'
        * 'either'
        """
        return self.parent().driver.trigger.ac_line.slope

    @slope.setter
    def slope(self, value):
        self.parent().driver.trigger.ac_line.slope = value
        self.slope_changed.emit(self.parent().driver.trigger.ac_line.slope)


class ProbeAutoSenseMixin(scope.ProbeAutoSenseInterface):
    """
    Extension IVI methods for oscilloscopes supporting probe attenuation sensing

    Implement as Mixin for channels[]
    """
    probe_attenuation_auto_changed = Signal(bool)

    @property
    def probe_attenuation_auto(self):
        """
        If this attribute is True, the driver configures the oscilloscope to sense
        the attenuation of the probe automatically.

        If this attribute is False, the driver disables the automatic probe sense
        and configures the oscilloscope to use the value of the Probe Attenuation
        attribute.

        The actual probe attenuation the oscilloscope is currently using can be
        determined from the Probe Attenuation attribute.

        Setting the Probe Attenuation attribute also sets the Probe Attenuation
        Auto attribute to false.
        """
        return self.parent().driver.channels[self._channel_index].probe_attenuation_auto

    @probe_attenuation_auto.setter
    def probe_attenuation_auto(self, value):
        self.parent().driver.channels[self._channel_index].probe_attenuation_auto = value
        self.probe_attenuation_auto_changed.emit(
            self.parent().driver.channels[self._channel_index].probe_attenuation_auto)


class ContinuousAcquisitionMixin(scope.ContinuousAcquisitionInterface):
    """
    The IviScopeContinuousAcquisition extension group provides support for oscilloscopes that can
    perform a continuous acquisition.
    """
    continuous_changed = Signal(bool)

    @property
    def continuous(self):
        """
        Specifies whether the oscilloscope continuously initiates waveform acquisition. If the
        end-user sets this attribute to True, the oscilloscope immediately waits for another trigger
        after the previous waveform acquisition is complete. Setting this attribute to True is
        useful when the end-user requires continuous updates of the oscilloscope display. This
        specification does not define the behavior of the read waveform and fetch waveform functions
        when this attribute is set to True. The behavior of these functions is instrument specific.
        """
        return self.parent().driver.trigger.continuous

    @continuous.setter
    def continuous(self, value):
        self.parent().driver.trigger.continuous = value
        self.continuous_changed.emit(value)


class AverageAcquisitionMixin(scope.AverageAcquisitionInterface):
    """
    The IviScopeAverageAcquisition extension group provides support for oscilloscopes that can
    perform the average acquisition.

    This interface has to be implemented by the Acquisition class.
    """
    number_of_averages_changed = Signal(int)

    @property
    def number_of_averages(self):
        """
        Specifies the number of waveform the oscilloscope acquires and averages. After the
        oscilloscope acquires as many waveforms as this attribute specifies, it returns to the
        idle state. This attribute affects instrument behavior only when the Acquisition Type
        attribute is set to Average.
        """
        return self.parent().driver.acquisition.number_of_averages

    @number_of_averages.setter
    def number_of_averages(self, value):
        self.parent().driver.acquisition.number_of_averages = value
        self.number_of_averages_changed.emit(value)


class SampleModeMixin(scope.SampleModeInterface):
    """
    Extension IVI methods for oscilloscopes supporting equivalent and real time acquisition

    Implement as mixin to AcquisitionInterface
    """
    sample_mode_changed = Signal(str)

    @property
    def sample_mode(self):
        """
        Returns the sample mode the oscilloscope is currently using.

        Values:
        * 'real_time'
        * 'equivalent_time'
        """
        return self.parent().driver.acquisition.sample_mode

    @sample_mode.setter
    def sample_mode(self, value):
        self.parent().driver.acquisition.sample_mode = value
        self.sample_mode_changed.emit(self.parent().driver.acquisition.sample_mode)


class TriggerModifierMixin(scope.TriggerModifierInterface):
    """
    Extension IVI methods for oscilloscopes supporting specific triggering subsystem behavior in the absence of a trigger

    Implement as mixin to TriggerInterface
    """
    modifier_changed = Signal(str)

    @property
    def modifier(self):
        """
        Specifies the trigger modifier. The trigger modifier determines the
        oscilloscope's behavior in the absence of the configured trigger.

        Values:
        * 'none'
        * 'auto'
        * 'auto_level'
        """
        return self.parent().driver.trigger.modifier

    @modifier.setter
    def modifier(self, value):
        self.parent().driver.trigger.modifier = value
        self.modifier_changed.emit(self.parent().driver.trigger.modifier)


class AutoSetupMixin(scope.AutoSetupInterface):
    """
    The IviScopeAutoSetup extension group provides support for oscilloscopes that can perform an
    auto-setup operation.

    This interface has to be implemented by the Measurement class.
    """

    def auto_setup(self):
        """
        This function performs an auto-setup on the instrument.
        """
        self.parent().driver.measurement.auto_setup()


class WaveformMeasurementReferenceLevel(QObject, scope.WaveformMeasurementReferenceLevelInterface):
    """
    Extension IVI methods for oscilloscopes supporting waveform measurements

    Implement as reference_level in main class.
    """
    high_changed = Signal(float)
    middle_changed = Signal(float)
    low_changed = Signal(float)

    @property
    def high(self):
        """
        Specifies the high reference the oscilloscope uses for waveform
        measurements. The value is a percentage of the difference between the
        Voltage High and Voltage Low.
        """
        return self.parent().driver.reference_level.high

    @high.setter
    def high(self, value):
        self.parent().driver.reference_level.high = value
        self.high_changed.emit(self.parent().driver.reference_level.high)

    @property
    def middle(self):
        """
        Specifies the middle reference the oscilloscope uses for waveform
        measurements. The value is a percentage of the difference between the
        Voltage High and Voltage Low.
        """
        return self.parent().driver.reference_level.middle

    @middle.setter
    def middle(self, value):
        self.parent().driver.reference_level.middle = value
        self.middle_changed.emit(self.parent().driver.reference_level.middle)

    @property
    def low(self):
        """
        Specifies the low reference the oscilloscope uses for waveform
        measurements. The value is a percentage of the difference between the
        Voltage High and Voltage Low.
        """
        return self.parent().driver.reference_level.low

    @low.setter
    def low(self, value):
        self.parent().driver.reference_level.low = value
        self.low_changed.emit(self.parent().driver.reference_level.low)

    def configure(self, low, middle, high):
        """
        This function configures the reference levels for waveform measurements.
        Call this function before calling the Read Waveform Measurement or Fetch
        Waveform Measurement to take waveform measurements.
        """
        self.parent().driver.reference_level.configure(low, middle, high)


class WaveformMeasurementChannelMeasurementMixin(scope.WaveformMeasurementChannelMeasurementInterface):
    """
    Extension IVI methods for oscilloscopes supporting waveform measurements

    Implement as mixin for ChannelMeasurement class.
    """

    def fetch_waveform_measurement(self, measurement_function):
        """
        This function fetches a specified waveform measurement from a specific
        channel from a previously initiated waveform acquisition. If the channel
        is not enabled for the acquisition, this function returns the Channel Not
        Enabled error.

        This function obtains a waveform measurement and returns the measurement
        value. The end-user specifies a particular measurement type, such as rise
        time, frequency, and voltage peak-to-peak. The waveform on which the
        oscilloscope calculates the waveform measurement is from an acquisition
        that was previously initiated.

        Use the Initiate Acquisition function to start an acquisition on the
        channels that were enabled with the Configure Channel function. The
        oscilloscope acquires waveforms for the enabled channels concurrently. Use
        the Acquisition Status function to determine when the acquisition is
        complete. Call this function separately for each waveform measurement on a
        specific channel.

        The end-user can call the Read Waveform Measurement function instead of
        the Initiate Acquisition function. The Read Waveform Measurement function
        starts an acquisition on all enabled channels. It then waits for the
        acquisition to complete, obtains a waveform measurement on the specified
        channel, and returns the measurement value. Call this function separately
        to obtain any other waveform measurements on a specific channel.

        Configure the appropriate reference levels before calling this function to
        take a rise time, fall time, width negative, width positive, duty cycle
        negative, or duty cycle positive measurement.

        The end-user can configure the low, mid, and high references either by
        calling the Configure Reference Levels function or by setting the
        following attributes.

        * Measurement High Reference
        * Measurement Low Reference
        * Measurement Mid Reference

        This function does not check the instrument status. Typically, the
        end-user calls this function only in a sequence of calls to other
        low-level driver functions. The sequence performs one operation. The
        end-user uses the low-level functions to optimize one or more aspects of
        interaction with the instrument. Call the Error Query function at the
        conclusion of the sequence to check the instrument status.

        Values for measurement_function:
        * 'rise_time'
        * 'fall_time'
        * 'frequency'
        * 'period'
        * 'voltage_rms'
        * 'voltage_peak_to_peak'
        * 'voltage_max'
        * 'voltage_min'
        * 'voltage_high'
        * 'voltage_low'
        * 'voltage_average'
        * 'width_negative'
        * 'width_positive'
        * 'duty_cycle_negative'
        * 'duty_cycle_positive'
        * 'amplitude'
        * 'voltage_cycle_rms'
        * 'voltage_cycle_average'
        * 'overshoot'
        * 'preshoot'
        """
        return self.parent().driver.channels[
            self._channel_index].measurement.fetch_waveform_measurement(measurement_function)

    def read_waveform_measurement(self, measurement_function, maximum_time):
        """
        This function initiates a new waveform acquisition and returns a specified
        waveform measurement from a specific channel.

        This function initiates an acquisition on the channels that the end-user
        enables with the Configure Channel function. If the channel is not enabled
        for the acquisition, this function returns Channel Not Enabled error. It
        then waits for the acquisition to complete, obtains a waveform measurement
        on the channel the end-user specifies, and returns the measurement value.
        The end-user specifies a particular measurement type, such as rise time,
        frequency, and voltage peak-to-peak.

        If the oscilloscope did not complete the acquisition within the time
        period the user specified with the MaxTimeMilliseconds parameter, the
        function returns the Max Time Exceeded error.

        The end-user can call the Fetch Waveform Measurement function separately
        to obtain any other waveform measurement on a specific channel without
        initiating another acquisition.

        The end-user must configure the appropriate reference levels before
        calling this function. Configure the low, mid, and high references either
        by calling the Configure Reference Levels function or by setting the
        following attributes.

        * Measurement High Reference
        * Measurement Low Reference
        * Measurement Mid Reference
        """
        return self.parent().driver.channels[
            self._channel_index].measurement.read_waveform_measurement(measurement_function, maximum_time)


class MinMaxWaveformAcquisitionMixin(scope.MinMaxWaveformAcquisitionInterface):
    """
    Extension IVI methods for oscilloscopes supporting minimum and maximum waveform acquisition

    Implement in acquisition.
    """
    number_of_envelopes_changed = Signal(int)

    @property
    def number_of_envelopes(self):
        """
        When the end-user sets the Acquisition Type attribute to Envelope, the
        oscilloscope acquires multiple waveforms. After each waveform acquisition,
        the oscilloscope keeps the minimum and maximum values it finds for each
        point in the waveform record. This attribute specifies the number of
        waveforms the oscilloscope acquires and analyzes to create the minimum and
        maximum waveforms. After the oscilloscope acquires as many waveforms as
        this attribute specifies, it returns to the idle state. This attribute
        affects instrument operation only when the Acquisition Type attribute is
        set to Envelope.
        """
        return self.parent().driver.acquisition.number_of_envelopes

    @number_of_envelopes.setter
    def number_of_envelopes(self, value):
        self.parent().driver.acquisition.number_of_envelopes = value
        self.number_of_envelopes_changed.emit(value)


class MinMaxWaveformChannelMeasurementMixin(scope.MinMaxWaveformChannelMeasurementInterface):
    """
    Extension IVI methods for oscilloscopes supporting minimum and maximum waveform acquisition

    Implement in channels[].measurement
    """

    def fetch_waveform_min_max(self):
        """
        This function returns the minimum and maximum waveforms that the
        oscilloscope acquires for the specified channel. If the channel is not
        enabled for the acquisition, this function returns the Channel Not Enabled
        error.

        The waveforms are from a previously initiated acquisition. Use this
        function to fetch waveforms when the acquisition type is set to Peak
        Detect or Envelope. If the acquisition type is not one of the listed
        types, the function returns the Invalid Acquisition Type error.

        Use the Initiate Acquisition function to start an acquisition on the
        enabled channels. The oscilloscope acquires the min/max waveforms for the
        enabled channels concurrently. Use the Acquisition Status function to
        determine when the acquisition is complete. The end-user must call this
        function separately for each enabled channel to obtain the min/max
        waveforms.

        The end-user can call the Read Min Max Waveform function instead of the
        Initiate Acquisition function. The Read Min Max Waveform function starts
        an acquisition on all enabled channels, waits for the acquisition to
        complete, and returns the min/max waveforms for the specified channel. You
        call this function to obtain the min/max waveforms for each of the
        remaining channels.

        After this function executes, each element in the MinWaveform and
        MaxWaveform parameters is either a voltage or a value indicating that the
        oscilloscope could not sample a voltage.

        The return value is a list of (x, y_min, y_max) tuples that represent the
        time and voltage of each data point.  Either of the y points may be NaN in
        the case that the oscilloscope could not sample the voltage.

        The end-user configures the interpolation method the oscilloscope uses
        with the Acquisition.Interpolation property. If interpolation is disabled,
        the oscilloscope does not interpolate points in the waveform. If the
        oscilloscope cannot sample a value for a point in the waveform, the driver
        sets the corresponding element in the waveformArray to an IEEE-defined NaN
        (Not a Number) value. Check for this value with math.isnan() or
        numpy.isnan(). Check an entire array with

        any(any(math.isnan(b) for b in a) for a in waveform)

        This function does not check the instrument status. Typically, the
        end-user calls this function only in a sequence of calls to other
        low-level driver functions. The sequence performs one operation. The
        end-user uses the low-level functions to optimize one or more aspects of
        interaction with the instrument. Call the Error Query function at the
        conclusion of the sequence to check the instrument status.
        """
        return self.parent().driver.channels[self._channel_index].measurement.fetch_waveform_min_max()

    def read_waveform_min_max(self):
        """
        This function initiates new waveform acquisition and returns minimum and
        maximum waveforms from a specific channel. If the channel is not enabled
        for the acquisition, this function returns the Channel Not Enabled error.

        This function is used when the Acquisition Type is Peak Detect or
        Envelope. If the acquisition type is not one of the listed types, the
        function returns the Invalid Acquisition Type error.

        This function initiates an acquisition on the enabled channels. It then
        waits for the acquisition to complete, and returns the min/max waveforms
        for the specified channel. Call the Fetch Min Max Waveform function to
        obtain the min/max waveforms for each of the remaining enabled channels
        without initiating another acquisition. If the oscilloscope did not
        complete the acquisition within the time period the user specified with
        the max_time parameter, the function returns the Max Time Exceeded error.

        The return value is a list of (x, y_min, y_max) tuples that represent the
        time and voltage of each data point.  Either of the y points may be NaN in
        the case that the oscilloscope could not sample the voltage.

        The end-user configures the interpolation method the oscilloscope uses
        with the Acquisition.Interpolation property. If interpolation is disabled,
        the oscilloscope does not interpolate points in the waveform. If the
        oscilloscope cannot sample a value for a point in the waveform, the driver
        sets the corresponding element in the waveformArray to an IEEE-defined NaN
        (Not a Number) value. Check for this value with math.isnan() or
        numpy.isnan(). Check an entire array with

        any(any(math.isnan(b) for b in a) for a in waveform)

        This function does not check the instrument status. Typically, the
        end-user calls this function only in a sequence of calls to other
        low-level driver functions. The sequence performs one operation. The
        end-user uses the low-level functions to optimize one or more aspects of
        interaction with the instrument. Call the Error Query function at the
        conclusion of the sequence to check the instrument status.
        """
        return self.parent().driver.channels[self._channel_index].measurement.read_waveform_min_max()


# **************************************************************************************************


class PythonIviScope(PythonIviBase, scope.ScopeInterface):
    """
    Module for accessing oscilloscopes via PythonIVI library
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._acquisition = None
        self._measurement = None
        self._trigger = None
        self.channels = []
        self._reference_level = None

    def on_activate(self):
        super().on_activate()

        # find all base classes of driver
        driver_capabilities = inspect.getmro(type(self.driver))

        # dynamic acquisition class generator
        class IviAcquisition(Acquisition):
            pass
        if ivi.scope.Interpolation in driver_capabilities:
            IviAcquisition.__bases__ = IviAcquisition.__bases__ + (InterpolationAcquisitionMixin, )
        if ivi.scope.AverageAcquisition in driver_capabilities:
            IviAcquisition.__bases__ = IviAcquisition.__bases__ + (AverageAcquisitionMixin, )
        if ivi.scope.AutoSetup in driver_capabilities:
            IviAcquisition.__bases__ = IviAcquisition.__bases__ + (AutoSetupMixin,)
        if ivi.scope.MinMaxWaveform in driver_capabilities:
            IviAcquisition.__bases__ = IviAcquisition.__bases__ + (MinMaxWaveformAcquisitionMixin, )
        if ivi.scope.SampleMode in driver_capabilities:
            IviAcquisition.__bases__ = IviAcquisition.__bases__ + (SampleModeMixin, )
        self._acquisition = IviAcquisition(parent=self)

        # dynamic measurement class generator
        class IviMeasurement(Measurement):
            pass
        self._measurement = IviMeasurement(parent=self)

        # dynamic trigger class generator
        class IviTrigger(Trigger):
            pass
        if ivi.scope.ContinuousAcquisition in driver_capabilities:
            IviTrigger.__bases__ = IviTrigger.__bases__ + (ContinuousAcquisitionMixin, )
        if ivi.scope.TriggerModifier in driver_capabilities:
            IviTrigger.__bases__ = IviTrigger.__bases__ + (TriggerModifierMixin, )
        self._trigger = IviTrigger(parent=self)

        self.channels = []
        for ii in range(len(self.driver.channels)):
            class IviChannelMeasurement(ChannelMeasurement):
                pass
            if ivi.scope.WaveformMeasurement in driver_capabilities:
                IviChannelMeasurement.__bases__ = IviChannelMeasurement.__bases__ + (WaveformMeasurementChannelMeasurementMixin,)
            if ivi.scope.MinMaxWaveform in driver_capabilities:
                IviChannelMeasurement.__bases__ = IviChannelMeasurement.__bases__ + \
                                                  (MinMaxWaveformChannelMeasurementMixin, )
            channel_measurement = IviChannelMeasurement(channel_index=ii, parent=self)

            class IviChannel(Channel):
                pass
            if ivi.scope.ProbeAutoSense in driver_capabilities:
                IviChannel.__bases__ = IviChannel.__bases__ + (ProbeAutoSenseMixin, )
            self.channels.append(IviChannel(channel_index=ii, channel_measurement=channel_measurement, parent=self))

        if (ivi.scope.WaveformMeasurement in driver_capabilities):
            self._reference_level = WaveformMeasurementReferenceLevel(parent=self)

    def on_deactivate(self):
        super().on_deactivate()
        self._acquisition = None
        self._measurement = None
        self._trigger = None
        self.channels = []
        self._reference_level = None

    @property
    def acquisition(self):
        return self._acquisition

    @property
    def measurement(self):
        return self._measurement

    @property
    def trigger(self):
        return self._trigger

    @property
    def refererence_level(self):
        return self._reference_level