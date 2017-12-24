from core.module import Base, ConfigOption
from interface import scope

import importlib
from qtpy.QtCore import QObject
from qtpy.QtCore import Signal


class PythonIviBase(Base):
    driver = ConfigOption('driver', missing='error')
    uri = ConfigOption('uri', missing='error')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._driver_module = None
        self._driver_class = None
        self.driver = None

    def on_activate(self):
        # load driver package
        module_name, class_name = self.driver().rsplit('.', 1)
        self._driver_module = importlib.import_module(module_name)
        # instantiate class and connect to scope
        self._driver_class = getattr(self._driver_module, class_name)
        self.driver = self._driver_class(self.uri())

    def on_deactivate(self):
        self.driver = None
        self._driver_class = None
        self._driver_module = None


class Acquisition(QObject, scope.AcquisitionInterface):
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

    def __init__(self, channel_index, **kwargs):
        super().__init__(**kwargs)
        self._channel_index = channel_index

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
        return self.parent().driver.channel[self._channel_index].name

    @property
    def enabled(self):
        """
        If set to True, the oscilloscope acquires a waveform for the channel. If
        set to False, the oscilloscope does not acquire a waveform for the
        channel.
        """
        return self.parent().driver.channel[self._channel_index].enabled

    @enabled.setter
    def enabled(self, value):
        self.parent().driver.channel[self._channel_index].enabled = value
        self.enabled_changed.emit(value)

    @property
    def input_impedance(self):
        """
        Specifies the input impedance for the channel in Ohms.

        Common values are 50.0, 75.0, and 1,000,000.0.
        """
        return self.parent().driver.channel[self._channel_index].input_impedance

    @input_impedance.setter
    def input_impedance(self, value):
        self.parent().driver.channel[self._channel_index].input_impedance = value
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
        return self.parent().driver.channel[self._channel_index].input_frequency_max

    @input_frequency_max.setter
    def input_frequency_max(self, value):
        self.parent().driver.channel[self._channel_index].input_frequency_max = value
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
        return self.parent().driver.channel[self._channel_index].probe_attenuation

    @probe_attenuation.setter
    def probe_attenuation(self, value):
        self.parent().driver.channel[self._channel_index].probe_attenuation = value
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
        return self.parent().driver.channel[self._channel_index].coupling

    @coupling.setter
    def coupling(self, value):
        self.parent().driver.channel[self._channel_index].coupling = value
        self.coupling_changed.emit(value)

    @property
    def offset(self):
        """
        Specifies the location of the center of the range that the Vertical Range
        attribute specifies. The value is with respect to ground and is in volts.

        For example, to acquire a sine wave that spans between on 0.0 and 10.0
        volts, set this attribute to 5.0 volts.
        """
        return self.parent().driver.channel[self._channel_index].offset

    @offset.setter
    def offset(self, value):
        self.parent().driver.channel[self._channel_index].offset = value
        self.offset_changed.emit(value)

    @property
    def range(self):
        """
        Specifies the absolute value of the full-scale input range for a channel.
        The units are volts.

        For example, to acquire a sine wave that spans between -5.0 and 5.0 volts,
        set the Vertical Range attribute to 10.0 volts.
        """
        return self.parent().driver.channel[self._channel_index].range

    @range.setter
    def range(self, value):
        self.parent().driver.channel[self._channel_index].range = value
        self.range_changed.emit(value)

    def configure(self, vertical_range, offset, coupling, probe_attenuation, enabled):
        """
        This function configures the most commonly configured attributes of the
        oscilloscope channel sub-system. These attributes are the range, offset,
        coupling, probe attenuation, and whether the channel is enabled.
        """
        self.parent().driver.channel[self._channel_index].configure(
            vertical_range, offset, coupling, probe_attenuation, enabled)

    def configure_characteristics(self, input_impedance, input_frequency_max):
        """
        This function configures the attributes that control the electrical
        characteristics of the channel. These attributes are the input impedance
        and the maximum frequency of the input signal.
        """
        self.parent().driver.channel[self._channel_index].configure_characteristics(
            input_impedance, input_frequency_max)


class Measurement(QObject, scope.MeasurementInterface):
    """
    IVI Methods for Measurement
    """

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
        return self.parent().driver.measurement.fetch_waveform()

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
        return self.parent().driver.measurement.read_waveform()

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
        self.source_changed.emit(value)

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


# **************************************************************************************************

class PythonIviScope(PythonIviBase, scope.ScopeInterface):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._acquisition = Acquisition(parent=self)
        self._measurement = Measurement(parent=self)
        self._trigger = Trigger(parent=self)
        self._channel = []
        for ii in range(self.driver.channel_count):
            self._channel.append(Channel(channel_index=ii, parent=self))

    @property
    def acquisition(self):
        return self._acquisition

    @property
    def measurement(self):
        return self._measurement

    @property
    def trigger(self):
        return self._trigger
