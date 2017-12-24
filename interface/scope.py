"""
Missing extensions:
 - IviScopeWaveformMeasurement
 - IviScopeMinMaxWaveform
 - IviScopeProbeAttenuationAuto
 - IviScopeSampleMode
 - IviScopeTriggerModifier
"""

import abc
from core.util.interfaces import InterfaceMetaclass


class ScopeInterface(metaclass=InterfaceMetaclass):
    """
    Interface for oscilloscope driver implementation following the IVI specification.
    """

    @property
    @abc.abstractmethod
    def acquisition(self):
        """
        Object implementing Acquisition interface.
        """
        pass

    channels = []

    @property
    @abc.abstractmethod
    def measurement(self):
        """
        Object implementing Measurement interface.
        """
        pass

    @property
    @abc.abstractmethod
    def trigger(self):
        """
        Object implementing Trigger interface.
        """
        pass


class AcquisitionInterface(metaclass=InterfaceMetaclass):
    """
    The acquisition sub-system configures the acquisition type, the size of the waveform record,
    the length of time that corresponds to the overall waveform record, and the position of the
    first point in the waveform record relative to the Trigger Event.
    """

    @property
    @abc.abstractmethod
    def start_time(self):
        """
        Specifies the length of time from the trigger event to the first point in
        the waveform record. If the value is positive, the first point in the
        waveform record occurs after the trigger event. If the value is negative,
        the first point in the waveform record occurs before the trigger event.
        The units are seconds.
        """
        pass

    @start_time.setter
    def start_time(self, value):
        pass

    @property
    @abc.abstractmethod
    def type(self):
        """
        Specifies how the oscilloscope acquires data and fills the waveform record.

        Values:
        * 'normal'
        * 'high_resolution'
        * 'average'
        * 'peak_detect'
        * 'envelope'
        """
        pass

    @type.setter
    def type(self, value):
        pass

    @property
    @abc.abstractmethod
    def number_of_points_minimum(self):
        """
        Specifies the minimum number of points the end-user requires in the
        waveform record for each channel. The instrument driver uses the value the
        end-user specifies to configure the record length that the oscilloscope
        uses for waveform acquisition. If the instrument cannot support the
        requested record length, the driver shall configure the instrument to the
        closest bigger record length. The Horizontal Record Length attribute
        returns the actual record length.
        """
        pass

    @number_of_points_minimum.setter
    def number_of_points_minimum(self, value):
        pass

    @property
    @abc.abstractmethod
    def record_length(self):
        """
        Returns the actual number of points the oscilloscope acquires for each
        channel. The value is equal to or greater than the minimum number of
        points the end-user specifies with the Horizontal Minimum Number of Points
        attribute.

        Note: Oscilloscopes may use different size records depending on the value
        the user specifies for the Acquisition Type attribute.
        """
        pass

    @property
    @abc.abstractmethod
    def sample_rate(self):
        """
        Returns the effective sample rate of the acquired waveform using the
        current configuration. The units are samples per second.
        """
        pass

    @property
    @abc.abstractmethod
    def time_per_record(self):
        """
        Specifies the length of time that corresponds to the record length. The
        units are seconds.
        """

    @time_per_record.setter
    def time_per_record(self, value):
        pass

    @abc.abstractmethod
    def configure_record(self, time_per_record, minimum_number_of_points, acquisition_start_time):
        """
        This function configures the most commonly configured attributes of the
        oscilloscope acquisition sub-system. These attributes are the time per
        record, minimum record length, and the acquisition start time.
        """
        pass


class ChannelInterface(metaclass=InterfaceMetaclass):
    @property
    @abc.abstractmethod
    def name(self):
        """
        This attribute returns the repeated capability identifier defined by
        specific driver for the channel that corresponds to the index that the
        user specifies. If the driver defines a qualified channel name, this
        property returns the qualified name.
        """
        pass

    @property
    @abc.abstractmethod
    def enabled(self):
        """
        If set to True, the oscilloscope acquires a waveform for the channel. If
        set to False, the oscilloscope does not acquire a waveform for the
        channel.
        """
        pass

    @enabled.setter
    def enabled(self, value):
        pass

    @property
    @abc.abstractmethod
    def input_impedance(self):
        """
        Specifies the input impedance for the channel in Ohms.

        Common values are 50.0, 75.0, and 1,000,000.0.
        """
        pass

    @input_impedance.setter
    def input_impedance(self, value):
        pass

    @property
    @abc.abstractmethod
    def input_frequency_max(self):
        """
        Specifies the maximum frequency for the input signal you want the
        instrument to accommodate without attenuating it by more than 3dB. If the
        bandwidth limit frequency of the instrument is greater than this maximum
        frequency, the driver enables the bandwidth limit. This attenuates the
        input signal by at least 3dB at frequencies greater than the bandwidth
        limit.
        """
        pass

    @input_frequency_max.setter
    def input_frequency_max(self, value):
        pass

    @property
    @abc.abstractmethod
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
        pass

    @probe_attenuation.setter
    def probe_attenuation(self, value):
        pass

    @property
    @abc.abstractmethod
    def coupling(self):
        """
        Specifies how the oscilloscope couples the input signal for the channel.

        Values:

        * 'ac'
        * 'dc'
        * 'gnd'
        """
        pass

    @coupling.setter
    def coupling(self, value):
        pass

    @property
    @abc.abstractmethod
    def offset(self):
        """
        Specifies the location of the center of the range that the Vertical Range
        attribute specifies. The value is with respect to ground and is in volts.

        For example, to acquire a sine wave that spans between on 0.0 and 10.0
        volts, set this attribute to 5.0 volts.
        """
        pass

    @offset.setter
    def offset(self, value):
        pass

    @property
    @abc.abstractmethod
    def range(self):
        """
        Specifies the absolute value of the full-scale input range for a channel.
        The units are volts.

        For example, to acquire a sine wave that spans between -5.0 and 5.0 volts,
        set the Vertical Range attribute to 10.0 volts.
        """
        pass

    @range.setter
    def range(self, value):
        pass

    @abc.abstractmethod
    def configure(self, vertical_range, offset, coupling, probe_attenuation, enabled):
        """
        This function configures the most commonly configured attributes of the
        oscilloscope channel sub-system. These attributes are the range, offset,
        coupling, probe attenuation, and whether the channel is enabled.
        """
        pass

    @abc.abstractmethod
    def configure_characteristics(self, input_impedance, input_frequency_max):
        """
        This function configures the attributes that control the electrical
        characteristics of the channel. These attributes are the input impedance
        and the maximum frequency of the input signal.
        """
        pass


class MeasurementInterface(metaclass=InterfaceMetaclass):
    """
    IVI Methods for Measurement
    """

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
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
        pass

    @property
    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
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
        pass


class TriggerInterface(metaclass=InterfaceMetaclass):
    """
    The trigger sub-system configures the type of event that triggers the oscilloscope.
    """

    @property
    @abc.abstractmethod
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
        pass

    @coupling.setter
    def coupling(self, value):
        pass

    @property
    @abc.abstractmethod
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
        pass

    @holdoff.setter
    def holdoff(self, value):
        pass

    @property
    @abc.abstractmethod
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
        pass

    @level.setter
    def level(self, value):
        pass

    @property
    def edge(self):
        return self._edge

    @property
    @abc.abstractmethod
    def source(self):
        """
        Specifies the source the oscilloscope monitors for the trigger event. The
        value can be a channel name alias, a driver-specific channel string, or
        one of the values below.

        This attribute affects the instrument operation only when the Trigger Type
        is set to one of the following values: Edge Trigger, TV Trigger, Runt
        Trigger, Glitch Trigger, or Width Trigger.
        """
        pass

    @source.setter
    def source(self, value):
        pass

    @property
    @abc.abstractmethod
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
        pass

    @type.setter
    def type(self, value):
        pass

    @abc.abstractmethod
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


class EdgeTriggerInterface(metaclass=InterfaceMetaclass):
    """
    IVI methods for Edge triggering
    """

    @property
    @abc.abstractmethod
    def slope(self):
        """
        Specifies whether a rising or a falling edge triggers the oscilloscope.

        This attribute affects instrument operation only when the Trigger Type
        attribute is set to Edge Trigger.

        Values:
         * 'positive'
         * 'negative'
        """
        pass

    @slope.setter
    def slope(self, value):
        pass

    @abc.abstractmethod
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
        pass


# ************************ EXTENSIONS **************************************************************

class InterpolationAcquisitionInterface(metaclass=InterfaceMetaclass):
    """
    The IviScopeInterpolation extension group defines extensions for oscilloscopes capable of
    interpolating values in the waveform record that the oscilloscope’s acquisition sub-system was
    unable to digitize.

    This interface has to be implemented by the Acquisition class.
    """

    @property
    @abc.abstractmethod
    def interpolation(self):
        """
        Specifies the interpolation method the oscilloscope uses when it cannot
        resolve a voltage for every point in the waveform record.

        Values:
        * 'none'
        * 'sinex'
        * 'linear'
        """
        pass

    @interpolation.setter
    def interpolation(self, value):
        pass


class TVTriggerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for oscilloscopes supporting TV triggering
    """

    @property
    @abc.abstractmethod
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
        pass

    @property
    @abc.abstractmethod
    def line_number(self):
        """
        Specifies the line on which the oscilloscope triggers. The driver uses
        this attribute when the TV Trigger Event is set to TV Event Line Number.
        The line number setting is independent of the field. This means that to
        trigger on the first line of the second field, the user must configure
        the line number to the value of 263 (if we presume that field one had 262
        lines).
        """
        pass

    def polarity(self):
        """
        Specifies the polarity of the TV signal.

        Values:
        * 'positive'
        * 'negative'
        """
        pass

    @property
    @abc.abstractmethod
    def signal_format(self):
        """
        Specifies the format of TV signal on which the oscilloscope triggers.

        Values:
        * 'ntsc'
        * 'pal'
        * 'secam'
        """
        pass

    @abc.abstractmethod
    def configure(self):
        """
        This function configures the oscilloscope for TV triggering. It configures
        the TV signal format, the event and the signal polarity.

        This function affects instrument behavior only if the trigger type is TV
        Trigger. Set the Trigger Type and Trigger Coupling before calling this
        function.
        """

class RuntTriggerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for oscilloscopes supporting runt triggering
    """

    @property
    @abc.abstractmethod
    def threshold_high(self):
        """
        Specifies the high threshold the oscilloscope uses for runt triggering.
        The units are volts.
        """
        pass

    @property
    @abc.abstractmethod
    def threshold_low(self):
        """
        Specifies the low threshold the oscilloscope uses for runt triggering.
        The units are volts.
        """
        pass

    @property
    @abc.abstractmethod
    def polarity(self):
        """
        Specifies the polarity of the runt that triggers the oscilloscope.

        Values:
        * 'positive'
        * 'negative'
        * 'either'
        """
        pass

    @abc.abstractmethod
    def configure(self):
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
        pass


class GlitchTriggerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for oscilloscopes supporting glitch triggering
    """

    @property
    @abc.abstractmethod
    def condition(self):
        """
        Specifies the glitch condition. This attribute determines whether the
        glitch trigger happens when the oscilloscope detects a pulse with a
        width less than or greater than the width value.

        Values:
        * 'greater_than'
        * 'less_than'
        """
        pass

    @property
    @abc.abstractmethod
    def polarity(self):
        """
        Specifies the polarity of the glitch that triggers the oscilloscope.

        Values:
        * 'positive'
        * 'negative'
        * 'either'
        """
        pass

    @property
    @abc.abstractmethod
    def width(self):
        """
        Specifies the glitch width. The units are seconds. The oscilloscope
        triggers when it detects a pulse with a width less than or greater than
        this value, depending on the Glitch Condition attribute.
        """
        pass

    @abc.abstractmethod
    def configure(self):
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
        pass


class WidthTriggerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for oscilloscopes supporting width triggering
    """

    @property
    @abc.abstractmethod
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
        pass

    @property
    @abc.abstractmethod
    def threshold_high(self):
        """
        Specifies the high width threshold time. Units are seconds.
        """
        pass

    @property
    @abc.abstractmethod
    def threshold_low(self):
        """
        Specifies the low width threshold time. Units are seconds.
        """
        pass

    @property
    @abc.abstractmethod
    def polarity(self):
        """
        Specifies the polarity of the pulse that triggers the oscilloscope.

        Values:
        * 'positive'
        * 'negative'
        * 'either'
        """
        pass

    @abc.abstractmethod
    def configure(self):
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
        pass


class AcLineTriggerInterface(metaclass=InterfaceMetaclass):
    """
    Extension IVI methods for oscilloscopes supporting AC line triggering
    """

    @property
    @abc.abstractmethod
    def slope(self):
        """
        Specifies the slope of the zero crossing upon which the scope triggers.

        Values:
        * 'positive'
        * 'negative'
        * 'either'
        """
        pass


class ContinuousAcquisitionTriggerInterface(metaclass=InterfaceMetaclass):
    """
    The IviScopeContinuousAcquisition extension group provides support for oscilloscopes that can
    perform a continuous acquisition.

    This interface has to be implemented by the Trigger class.
    """
    @property
    @abc.abstractmethod
    def continuous(self):
        """
        Specifies whether the oscilloscope continuously initiates waveform acquisition. If the
        end-user sets this attribute to True, the oscilloscope immediately waits for another trigger
        after the previous waveform acquisition is complete. Setting this attribute to True is
        useful when the end-user requires continuous updates of the oscilloscope display. This
        specification does not define the behavior of the read waveform and fetch waveform functions
        when this attribute is set to True. The behavior of these functions is instrument specific.
        """
        pass

    @continuous.setter
    def continuous(self, value):
        pass


class AverageAcquisitionInterface(metaclass=InterfaceMetaclass):
    """
    The IviScopeAverageAcquisition extension group provides support for oscilloscopes that can
    perform the average acquisition.

    This interface has to be implemented by the Acquisition class.
    """
    @property
    @abc.abstractmethod
    def number_of_averages(self):
        """
        Specifies the number of waveform the oscilloscope acquires and averages. After the
        oscilloscope acquires as many waveforms as this attribute specifies, it returns to the
        idle state. This attribute affects instrument behavior only when the Acquisition Type
        attribute is set to Average.
        """
        pass

    @number_of_averages.setter
    def number_of_averages(self, value):
        pass


class AutoSetupInterface(metaclass=InterfaceMetaclass):
    """
    The IviScopeAutoSetup extension group provides support for oscilloscopes that can perform an
    auto-setup operation.

    This interface has to be implemented by the Measurement class.
    """

    def auto_setup(self):
        """
        This function performs an auto-setup on the instrument.
        """
        pass

