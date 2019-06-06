# -*- coding: utf-8 -*-
"""
This file contains the implementation of the pythonIvi interface for scopes.

The main class is ::PythonIviScope::

Example configuration

hardware:
    dsos204a:
        module.Class: 'ivi.scope.python_ivi_scope.PythonIviScope'
        driver: 'ivi.agilent.agilentDSOS204A.agilentDSOS204A'
        uri: 'TCPIP::192.168.1.1::INSTR'


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

from interface.ivi.inherent_capabilities_interface import InherentCapabilitiesInterface
from interface.ivi import scope_interface as scope_ivi_interface
from ..python_ivi_base import PythonIviBase

import abc
import inspect
from qtpy.QtCore import QObject
from qtpy.QtCore import Signal
from namespace import Namespace
import ivi.scope


class QtInterfaceMetaclass(type(QObject), abc.ABCMeta):
    pass


class _Scope(InherentCapabilitiesInterface, scope_ivi_interface.ScopeIviInterface):
    def close(self):
        """
        When the user finishes using an IVI driver session in IVI-C and IVI-COM, the user must call the Close
        function. This function closes the I/O session to the instrument. This function may put the instrument into
        an idle state before closing the I/O session.
        """
        self.driver.close()

    @Namespace
    class utility(QObject, InherentCapabilitiesInterface.utility, metaclass=QtInterfaceMetaclass):
        def error_query(self):
            """
            Queries the instrument and returns instrument specific error information.

            Generally, the user calls this function after another function in the IVI driver returns the Instrument
            Status error. The IVI specific driver returns the Instrument Status error when the instrument indicates that
            it encountered an error and its error queue is not empty. Error Query extracts an error out of the
            instrument's error queue. For instruments that have status registers but no error queue, the IVI specific
            driver emulates an error queue in software.

            :return: (error code, error message)
            """
            return self.root.driver.utility.error_query()

        def reset(self):
            """
            Resets the instrument.

            This function performs the following actions:
                - Places the instrument in a known state. In an IEEE 488.2 instrument, the Reset function sends the
                  command string "*RST" to the instrument.
                - Configures instrument options on which the IVI specific driver depends. A specific driver might
                  enable or disable headers or enable binary mode for waveform transfers.

            The user can either call the Reset function separately or specify that it be called from the __init__
            function. The Initialize function performs additional operations after performing the reset operation to
            place the instrument in a state more suitable for interchangeable programming. To reset the device and
            perform these additional operations, call the Reset With Defaults function instead of the Reset function.

            Exceptions: ResetNotSupportedException: Raised if the instrument does not support reset.
            """
            self.root.driver.utility.reset()

        def reset_with_defaults(self):
            """
            Resets the instrument and configures initial settings.

            The Reset With Defaults function performs the same operations that the Reset function performs and then
            performs the following additional operations in the specified order:
                - Disables the class extension capability groups that the IVI specific driver implements.
                - If the class specification with which the IVI specific driver is compliant defines initial values for
                  attributes, this function sets those attributes to the initial values that the class specification
                  defines.
                - Configures the initial settings for the specific driver and instrument based on the information
                  retrieved from the IVI configuration store when the instrument driver session was initialized.

            Notice that the __init__ function also performs these functions. To place the instrument and the IVI
            specific driver in the exact same state that they attain when the user calls the Initialize function, the
            user must first call the Close function and then the Initialize function.
            """
            self.root.driver.utility.reset_with_defaults()

        def self_test(self):
            """
            Causes the instrument to perform a self test.

            Self Test waits for the instrument to complete the test. It then queries the instrument for the results of
            the self test and returns the results to the user.

            If the instrument passes the self test, this function returns the tuple (0, 'Self test passed')

            :return: (result code, message)
            """
            return self.root.driver.utility.self_test()

    @Namespace
    class driver_operation(QObject, InherentCapabilitiesInterface.driver_operation, metaclass=QtInterfaceMetaclass):
        query_instrument_status_changed = Signal(bool)
        range_check_changed = Signal(bool)
        simulate_changed = Signal(bool)

        @property
        def cache(self):
            """
            Specifies whether the driver caches values of attributes.

            If True, the specific driver caches the value of attributes, and the IVI specific driver keeps track of the
            current instrument settings so that it can avoid sending redundant commands to the instrument. If False, the
            specific driver does not cache the value of attributes.

            The default value is True. When the user opens an instrument session through an IVI class driver or uses a
            logical name to initialize a specific driver, the user can override this value by specifying a value in the
            IVI configuration store. The Initialize function allows the user to override both the default value and the
            value that the user specifies in the IVI configuration store.
            """
            return self.root.driver.driver_operation.cache

        @property
        def driver_setup(self):
            """
            Returns the driver setup string.

            Returns the driver setup string that the user specified in the IVI configuration store when the instrument
            driver session was initialized or passes in the OptionString parameter of the Initialize function. Refer to
            Section 6.14, Initialize, for the restrictions on the format of the driver setup string.
            """
            return self.root.driver.driver_operation.driver_setup

        @property
        def io_resource_descriptor(self):
            """
            Returns the resource descriptor that the user specified for the physical device.

            The user specifies the resource descriptor by editing the IVI configuration store or by passing a resource
            descriptor to the Initialize function of the specific driver. Refer to Section 6.14, Initialize, for the
            restrictions on the contents of the resource descriptor string.
            """
            return self.root.driver.driver_operation.io_resource_descriptor

        @property
        def logical_name(self):
            """
            Returns the IVI logical name that the user passed to the Initialize function.

            If the user initialized the IVI specific driver directly and did not pass a logical name, then this
            attribute returns an empty string. Refer to IVI-3.5: Configuration Server Specification for restrictions
            on the format of IVI logical names.
            """
            return self.root.driver.driver_operation.logical_name

        @property
        def query_instrument_status(self):
            """
            Specifies whether the IVI specific driver queries the instrument status at the end of each user operation.

            If True, the IVI specific driver queries the instrument status at the end of each user operation. If False,
            the IVI specific driver does not query the instrument status at the end of each user operation.
            Querying the instrument status is very useful for debugging. After validating the program, the user can set
            this attribute to False to disable status checking and maximize performance. The user specifies this value
            for the entire IVI driver session.
            The default value is False. When the user opens an instrument session through an IVI class driver or uses a
            logical name to initialize an IVI specific driver, the user can override this value by specifying a value in
            the  IVI configuration store. The Initialize function allows the user to override both the default value and
            the value that the user specifies in the IVI configuration store.

            Compliance notes:

            1. The IVI specific driver shall implement both the True and False values for this attribute.
            2. If the instrument status can be queried for its status and this attribute is set to True, then the IVI
               specific driver checks the instrument status at the end of every call by the user to a function that
               accesses the instrument.
            3. If the instrument status cannot be queried independently of user operations, then this attribute has no
               effect on the behavior of the IVI specific driver.
            """
            return self.root.driver.driver_operation.query_instrument_status

        @query_instrument_status.setter
        def query_instrument_status(self, value):
            self.root.driver.driver_operation.query_instrument_status = value
            self.query_instrument_status_changed.emit(value)

        def invalidate_all_attributes(self):
            """
            This function invalidates the cached values of all attributes for the session.
            """
            return self.root.driver.driver_operation.invalidate_all_attributes()

        @property
        def range_check(self):
            """
            Specifies whether the driver validates attributes and function parameters.

            If True, the IVI specific driver validates attribute values and function parameters. If False, the IVI
            specific driver does not validate attribute values and function parameters.

            If range check is enabled, the specific driver validates the parameter values that users pass to driver
            functions. Validating attribute values and function parameters is useful for debugging. After validating the
            program, the user can set this attribute to False to disable range checking and maximize performance.
            The default value is True. When the user opens an instrument session through an IVI class driver or uses a
            logical name to initialize an IVI specific driver, the user can override this value by specifying a value in
            the IVI configuration store. The Initialize function allows the user to override both the default value and
            the value that the user specifies in the IVI configuration store.

            Compliance notes:

            1. The IVI specific driver shall implement both the True and False values for this attribute.
            2. Regardless of the value to which the user sets this attribute, the IVI specific driver is not required to
               duplicate all range checking operations that the instrument firmware performs.
            3. If this attribute is set to False, the IVI specific driver does not perform range-checking operations
               that the specific driver developer considers non-essential and time consuming.
            """
            return self.root.driver.driver_operation.range_check

        @range_check.setter
        def range_check(self, value):
            self.root.driver.driver_operation.range_check = value
            self.range_check_changed.emit(value)

        @property
        def simulate(self):
            """
            Specifies whether the IVI specific driver simulates instrument driver I/O operations.

            If True, the IVI specific driver simulates instrument driver I/O operations. If False, the IVI specific
            driver communicates directly with the instrument.

            If simulation is enabled, the specific driver functions do not perform instrument I/O. For output parameters
            that represent instrument data, the specific driver functions return simulated values.
            The default value is False. When the user opens an instrument session through an IVI class driver or uses a
            logical name to initialize an IVI specific driver, the user can override this value by specifying a value in
            the IVI configuration store. The Initialize function allows the user to override both the default value and
            the value that the user specifies in the IVI configuration store.

            Compliance notes:

            1. The IVI specific driver shall implement both the True and False values for this attribute.
            2. When Simulate is set to True, the IVI specific driver may perform less rigorous range checking
               operations than when Simulate is set to False.
            3. If the IVI specific driver is initialized with Simulate set to True, the specific driver shall return the
               Cannot Change Simulation State error if the user attempts to set Simulate to False prior to calling the
               Close function.
            """
            return self.root.driver.driver_operation.simulate

        @simulate.setter
        def simulate(self, value):
            self.root.driver.driver_operation.simulate = value
            self.simulate_changed.emit(value)

    @Namespace
    class identity(QObject, InherentCapabilitiesInterface.identity, metaclass=QtInterfaceMetaclass):
        @property
        def group_capabilities(self):
            """
            List of strings with class capability group names.

            Returns a list that identifies the class capability groups that the IVI specific driver implements. The
            items in the list are capability group names that the IVI class specifications define.
            """
            return self.root.driver.identity.group_capabilities.split(',')

        @property
        def specification_major_version(self):
            """
            Major version number of the implemented class specification.

            Returns the major version number of the class specification in accordance with which the  software
            component was developed. The value is a positive integer value. If the software component is not compliant
            with a class specification, the software component returns zero as the value of this attribute.
            """
            return self.root.driver.identity.specification_major_version

        @property
        def specification_minor_version(self):
            """
            Minor version number of the implemented class specification.

            Returns the minor version number of the class specification in accordance with which the software
            component was developed. The value is a non-negative integer value. If the software component is not
            compliant with a class specification, the software component returns zero as the value of this attribute.
            :return:
            """
            return self.root.driver.identity.specification_minor_version

        @property
        def description(self):
            """
            Returns a brief description of the software component.


            If the driver is compiled for use in 64-bit applications, the description may include the
            following statement at the end identifying it as 64-bit. [Compiled for 64-bit.]
            If the underlying driver is based on IVI-COM, it shall include it.
            """
            return self.root.driver.identity.description

        @property
        def identifier(self):
            """
            Returns the case-sensitive unique identifier of the (IVI-COM or IVI.NET) software component.

            The string that this attribute returns contains a maximum of 32 characters including the NULL character.
            """
            return self.root.driver.identity.identifier

        @property
        def revision(self):
            """
            Returns version information about the software component.

            Refer to Section 3.1.2.2, Additional Compliance Rules for Revision String Attributes, for additional rules
            regarding this attribute.
            """
            return self.root.driver.identity.revision

        @property
        def vendor(self):
            """
            Returns the name of the vendor that supplies the IVI-COM or IVI.NET software component.
            """
            return self.root.driver.identity.vendor

        @property
        def instrument_firmware_revision(self):
            """
            Instrument specific string that contains the firmware revision information of the physical instrument.

            The IVI specific driver returns the value it queries from the instrument as the value of this attribute or
            a string indicating that it cannot query the instrument identity. In some cases, it is not possible for the
            specific driver to query the firmware revision of the instrument. This can occur when the Simulate
            attribute is set to True or if the instrument is not capable of returning the firmware revision. For these
            cases, the specific driver returns defined strings for this attribute. If the Simulate attribute is set
            to True, the specific driver returns “Not available while simulating” as the value of this attribute. If
            the instrument is not capable of returning the firmware version and the Simulate attribute is set to False,
            the specific driver returns “Cannot query from instrument” as the value of this attribute.
            """
            return self.root.driver.identity.instrument_firmware_revision

        @property
        def instrument_manufacturer(self):
            """
            Returns the name of the manufacturer of the instrument.

            The IVI specific driver returns the value it queries from the instrument as the value of this attribute or
            a string indicating that it cannot query the instrument identity.

            In some cases, it is not possible for the IVI specific driver to query the manufacturer of the instrument.
            This can occur when the Simulate attribute is set to True or if the instrument is not capable of returning
            the manufacturer’s name. For these cases, the specific driver returns defined strings for this attribute. If
            th Simulate attribute is set to True, the specific driver returns “Not available while simulating” as the
            value of this attribute. If the instrument is not capable of returning the manufacturer name and the
            Simulate attribute is set to False, the specific driver returns “Cannot query from instrument” as the
            value of this attribute.
            """
            return self.root.driver.identity.instrument_manufacturer

        @property
        def instrument_model(self):
            """
            Returns the model number or name of the physical instrument.

            The IVI specific driver returns the value it queries from the instrument or a string indicating that it
            cannot query the instrument identity. In some cases, it is not possible for the IVI specific driver to
            query the model number of the instrument. This can occur when the Simulate attribute is set to True or
            if the instrument is not capable of returning the model number. For these cases, the specific driver
            returns defined strings for this attribute. If the Simulate attribute is set to True, the specific driver
            returns 'Not available while simulating' as the value of this attribute. If the instrument is not capable
            of returning the model number and the Simulate attribute is set to False, the specific driver returns
            'Cannot query from instrument' as the value of this attribute.
            """
            return self.root.driver.identity.instrument_model

        @property
        def supported_instrument_models(self):
            """
            List of supported instrument model names.

            Returns a list of strings of names of instrument models with which the IVI specific driver is
            compatible. The string has no white space except possibly embedded in the instrument model names. An
            example of a list that this attribute might return is ['TKTDS3012','TKTDS3014','TKTDS3016'].

            It is not necessary for the list to include the abbreviation for the manufacturer if it is the same for all
            models. In the example above, it is valid for the attribute to return the string TDS3012,TDS3014,TDS3016.
            """
            return self.root.driver.identity.supported_instrument_models

    class acquisition(QObject,
                      scope_ivi_interface.ScopeIviInterface.acquisition,
                      metaclass=QtInterfaceMetaclass):
        """
        The acquisition sub-system configures the acquisition type, the size of the waveform record,
        the length of time that corresponds to the overall waveform record, and the position of the
        first point in the waveform record relative to the Trigger Event.
        """

        start_time_changed = Signal(float)
        type_changed = Signal(scope_ivi_interface.AcquisitionType)
        number_of_points_minimum_changed = Signal(int)
        time_per_record_changed = Signal(float)

        @property
        def start_time(self):
            return self.root.driver.acquisition.start_time

        @start_time.setter
        def start_time(self, value):
            self.root.driver.acquisition.start_time = value
            self.start_time_changed.emit(value)

        @property
        def type(self):
            mapper = {'normal': scope_ivi_interface.AcquisitionType.NORMAL,
                      'high_resolution': scope_ivi_interface.AcquisitionType.HIGH_RESOLUTION,
                      'average': scope_ivi_interface.AcquisitionType.AVERAGE,
                      'peak_detect': scope_ivi_interface.AcquisitionType.PEAK_DETECT,
                      'envelope': scope_ivi_interface.AcquisitionType.ENVELOPE}
            return mapper[self.root.driver.acquisition.type]

        @type.setter
        def type(self, value):
            mapper = {scope_ivi_interface.AcquisitionType.NORMAL: 'normal',
                      scope_ivi_interface.AcquisitionType.HIGH_RESOLUTION: 'high_resolution',
                      scope_ivi_interface.AcquisitionType.AVERAGE: 'average',
                      scope_ivi_interface.AcquisitionType.PEAK_DETECT: 'peak_detect',
                      scope_ivi_interface.AcquisitionType.ENVELOPE: 'envelope'}
            self.root.driver.acquisition.type = mapper[value]
            self.type_changed.emit(value)

        @property
        def number_of_points_minimum(self):
            return self.root.driver.acquisition.number_of_points_minimum

        @number_of_points_minimum.setter
        def number_of_points_minimum(self, value):
            self.root.driver.acquisition.number_of_points_minimum = value
            self.number_of_points_minimum_changed.emit(value)

        @property
        def record_length(self):
            return self.root.driver.acquisition.record_length

        @property
        def sample_rate(self):
            return self.root.driver.acquisition.sample_rate

        @property
        def time_per_record(self):
            return self.root.driver.acquisition.time_per_record

        @time_per_record.setter
        def time_per_record(self, value):
            self.root.driver.acquisition.time_per_record = value
            self.time_per_record_changed.emit(value)

        def configure_record(self, time_per_record, minimum_number_of_points, acquisition_start_time):
            self.root.driver.acquisition.configure_record(time_per_record,
                                                          minimum_number_of_points,
                                                          acquisition_start_time)
            self.time_per_record_changed.emit(time_per_record)
            self.number_of_points_minimum_changed.emit(minimum_number_of_points)
            self.start_time_changed.emit(acquisition_start_time)

    @property
    def _channel_count(self):
        return self.driver.channel_count

    class channels(QObject,
                   scope_ivi_interface.ScopeIviInterface.channels,
                   metaclass=QtInterfaceMetaclass):
        enabled_changed = Signal(bool)
        input_impedance_changed = Signal(int)
        input_frequency_maximum_changed = Signal(float)
        probe_attenuation_changed = Signal(float)
        coupling_changed = Signal(scope_ivi_interface.VerticalCoupling)
        offset_changed = Signal(float)
        range_changed = Signal(float)

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
            return self.root.driver.channels[self.index].name

        @property
        def enabled(self):
            """
            If set to True, the oscilloscope acquires a waveform for the channel. If
            set to False, the oscilloscope does not acquire a waveform for the
            channel.
            """
            return self.root.driver.channels[self.index].enabled

        @enabled.setter
        def enabled(self, value):
            self.root.driver.channels[self.index].enabled = value
            self.enabled_changed.emit(value)

        @property
        def input_impedance(self):
            """
            Specifies the input impedance for the channel in Ohms.

            Common values are 50.0, 75.0, and 1,000,000.0.
            """
            return self.root.driver.channels[self.index].input_impedance

        @input_impedance.setter
        def input_impedance(self, value):
            self.root.driver.channels[self.index].input_impedance = value
            self.input_impedance_changed.emit(value)

        @property
        def input_frequency_maximum(self):
            """
            Specifies the maximum frequency for the input signal you want the
            instrument to accommodate without attenuating it by more than 3dB. If the
            bandwidth limit frequency of the instrument is greater than this maximum
            frequency, the driver enables the bandwidth limit. This attenuates the
            input signal by at least 3dB at frequencies greater than the bandwidth
            limit.
            """
            return self.root.driver.channels[self.index].input_frequency_max

        @input_frequency_maximum.setter
        def input_frequency_maximum(self, value):
            self.root.driver.channels[self.index].input_frequency_max = value
            self.input_frequency_maximum_changed.emit(value)

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
            return self.root.driver.channels[self.index].probe_attenuation

        @probe_attenuation.setter
        def probe_attenuation(self, value):
            self.root.driver.channels[self.index].probe_attenuation = value
            self.probe_attenuation_changed.emit(value)

        @property
        def coupling(self):
            """
            Specifies how the oscilloscope couples the input signal for the channel.

            See also: VerticalCoupling
            """
            value = self.root.driver.channels[self.index].coupling
            mapper = {'ac': scope_ivi_interface.VerticalCoupling.AC,
                      'dc': scope_ivi_interface.VerticalCoupling.DC,
                      'gnd': scope_ivi_interface.VerticalCoupling.GND}
            return mapper[value]

        @coupling.setter
        def coupling(self, value):
            mapper = {scope_ivi_interface.VerticalCoupling.AC: 'ac',
                      scope_ivi_interface.VerticalCoupling.DC: 'dc',
                      scope_ivi_interface.VerticalCoupling.GND: 'gnd'}
            self.root.driver.channels[self.index].coupling = mapper[value]
            self.coupling_changed.emit(value)

        @property
        def offset(self):
            """
            Specifies the location of the center of the range that the Vertical Range
            attribute specifies. The value is with respect to ground and is in volts.

            For example, to acquire a sine wave that spans between on 0.0 and 10.0
            volts, set this attribute to 5.0 volts.
            """
            return self.root.driver.channels[self.index].offset

        @offset.setter
        def offset(self, value):
            self.root.driver.channels[self.index].offset = value
            self.offset_changed.emit(value)

        @property
        def range(self):
            """
            Specifies the absolute value of the full-scale input range for a channel.
            The units are volts.

            For example, to acquire a sine wave that spans between -5.0 and 5.0 volts,
            set the Vertical Range attribute to 10.0 volts.
            """
            return self.root.driver.channels[self.index].range

        @range.setter
        def range(self, value):
            self.root.driver.channels[self.index].range = value
            self.range_changed.emit(value)

        def configure(self, vertical_range, offset, coupling, probe_attenuation, enabled):
            """
            This function configures the most commonly configured attributes of the
            oscilloscope channel sub-system. These attributes are the range, offset,
            coupling, probe attenuation, and whether the channel is enabled.
            """
            self.root.driver.channels[self.index].configure(
                vertical_range, offset, coupling, probe_attenuation, enabled)

        def configure_characteristics(self, input_impedance, input_frequency_max):
            """
            This function configures the attributes that control the electrical
            characteristics of the channel. These attributes are the input impedance
            and the maximum frequency of the input signal.
            """
            self.root.driver.channels[self.index].configure_characteristics(
                input_impedance, input_frequency_max)

        class measurement(QObject,
                          scope_ivi_interface.ScopeIviInterface.channels.measurement,
                          metaclass=QtInterfaceMetaclass):
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
                return self.root.driver.channels[self.parent_namespace.index].measurement.fetch_waveform()
    
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
                return self.root.driver.channels[self.parent_namespace.index].measurement.read_waveform()

    class measurement(QObject,
                      scope_ivi_interface.ScopeIviInterface.measurement,
                      metaclass=QtInterfaceMetaclass):
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
    
            See also: AcquisitionStatus
            """
            mapper = {'complete': scope_ivi_interface.AcquisitionStatus.COMPLETE,
                      'in_progress': scope_ivi_interface.AcquisitionStatus.IN_PROGRESS,
                      'unknown': scope_ivi_interface.AcquisitionStatus.UNKNOWN}
            return mapper[self.root.driver.measurement.status]
    
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
            self.root.driver.measurement.abort()
    
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
            return self.root.driver.measurement.initiate()

    class trigger(QObject,
                  scope_ivi_interface.ScopeIviInterface.trigger,
                  metaclass=QtInterfaceMetaclass):
        """
        IVI Methods for Trigger
        """
        coupling_changed = Signal(scope_ivi_interface.TriggerCoupling)
        holdoff_changed = Signal(float)
        level_changed = Signal(float)
        source_changed = Signal(str)
        type_changed = Signal(str)

        @property
        def coupling(self):
            """
            Specifies how the oscilloscope couples the trigger source.
    
            See also: TriggerCoupling
            """
            value = self.root.driver.trigger.coupling
            mapper = {'ac': scope_ivi_interface.TriggerCoupling.AC,
                      'dc': scope_ivi_interface.TriggerCoupling.DC,
                      'lf_reject': scope_ivi_interface.TriggerCoupling.LF_REJECT,
                      'hf_reject': scope_ivi_interface.TriggerCoupling.HF_REJECT,
                      'noise_reject': scope_ivi_interface.TriggerCoupling.NOISE_REJECT}
            return mapper[value]
    
        @coupling.setter
        def coupling(self, value):
            mapper = {scope_ivi_interface.TriggerCoupling.AC: 'ac',
                      scope_ivi_interface.TriggerCoupling.DC: 'dc',
                      scope_ivi_interface.TriggerCoupling.HF_REJECT: 'hf_reject',
                      scope_ivi_interface.TriggerCoupling.LF_REJECT: 'lf_reject',
                      scope_ivi_interface.TriggerCoupling.NOISE_REJECT: 'noise_reject'}
            self.root.driver.trigger.coupling = mapper[value]
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
            return self.root.driver.trigger.holdoff
    
        @holdoff.setter
        def holdoff(self, value):
            self.root.driver.trigger.holdoff = value
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
            return self.root.driver.trigger.level
    
        @level.setter
        def level(self, value):
            self.root.driver.trigger.level = value
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
            return self.root.driver.trigger.source
    
        @source.setter
        def source(self, value):
            self.root.driver.trigger.source = value
            self.source_changed.emit(self.root.driver.trigger.source)
    
        @property
        def type(self):
            """
            Specifies the event that triggers the oscilloscope.
    
            See also: TriggerType
            """
            mapper = {'edge': scope_ivi_interface.TriggerType.EDGE,
                      'tv': scope_ivi_interface.TriggerType.TV,
                      'runt': scope_ivi_interface.TriggerType.RUNT,
                      'glitch': scope_ivi_interface.TriggerType.GLITCH,
                      'width': scope_ivi_interface.TriggerType.WIDTH,
                      'immediate': scope_ivi_interface.TriggerType.IMMEDIATE,
                      'ac_line': scope_ivi_interface.TriggerType.ACLINE}
            return mapper[self.root.driver.trigger.type]
    
        @type.setter
        def type(self, value):
            mapper = {scope_ivi_interface.TriggerType.EDGE: 'edge',
                      scope_ivi_interface.TriggerType.TV: 'tv',
                      scope_ivi_interface.TriggerType.RUNT: 'runt',
                      scope_ivi_interface.TriggerType.GLITCH: 'glitch',
                      scope_ivi_interface.TriggerType.WIDTH: 'width',
                      scope_ivi_interface.TriggerType.IMMEDIATE: 'immediate',
                      scope_ivi_interface.TriggerType.ACLINE: 'ac_line'}
            self.root.driver.trigger.type = mapper[value]
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
            self.root.driver.trigger.configure(trigger_type, holdoff)


        @Namespace
        class edge(QObject,
                   scope_ivi_interface.ScopeIviInterface.trigger.edge,
                   metaclass=QtInterfaceMetaclass):
            """
            IVI methods for Edge triggering
            """
            slope_changed = Signal(scope_ivi_interface.TriggerSlope)

            @property
            def slope(self):
                """
                Specifies whether a rising or a falling edge triggers the oscilloscope.

                This attribute affects instrument operation only when the Trigger Type
                attribute is set to Edge Trigger.

                See also: TriggerSlope
                """
                mapper = {'positive': scope_ivi_interface.TriggerSlope.POSITIVE,
                          'negative': scope_ivi_interface.TriggerSlope.NEGATIVE}
                return mapper[self.root.driver.trigger.edge.slope]

            @slope.setter
            def slope(self, value):
                mapper = {scope_ivi_interface.TriggerSlope.POSITIVE: 'positive',
                          scope_ivi_interface.TriggerSlope.NEGATIVE: 'negative'}
                self.root.driver.trigger.slope = mapper[value]
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
                return self.root.driver.trigger.edge.configure(source, level, slope)


# ************************ EXTENSIONS **************************************************************


class InterpolationExtension(scope_ivi_interface.InterpolationExtensionInterface):
    class acquisition(scope_ivi_interface.InterpolationExtensionInterface.acquisition):
        interpolation_changed = Signal(str)

        @property
        def interpolation(self):
            """
            Specifies the interpolation method the oscilloscope uses when it cannot
            resolve a voltage for every point in the waveform record.

            See also: Interpolation

            Values:
            * 'none'
            * 'sinex'
            * 'linear'
            """
            mapper = {'none': scope_ivi_interface.Interpolation.NONE,
                      'sinex': scope_ivi_interface.Interpolation.SINEXOVERX,
                      'linear': scope_ivi_interface.Interpolation.LINEAR}
            return mapper[self.root.driver.acquisition.interpolation]

        @interpolation.setter
        def interpolation(self, value):
            mapper = {scope_ivi_interface.Interpolation.NONE: 'none',
                      scope_ivi_interface.Interpolation.SINEXOVERX: 'sinex',
                      scope_ivi_interface.Interpolation.LINEAR: 'linear'}
            self.root.driver.acquisition.interpolation = mapper[value]
            self.interpolation_changed.emit(value)


class TVTriggerExtension(scope_ivi_interface.TVTriggerExtensionInterface):
    """
    Extension IVI methods for oscilloscopes supporting TV triggering
    """
    class trigger:
        @Namespace
        class tv(QObject,
                 scope_ivi_interface.TVTriggerExtensionInterface.trigger.tv,
                 metaclass=QtInterfaceMetaclass):
            trigger_event_changed = Signal(scope_ivi_interface.TVTriggerEvent)
            line_number_changed = Signal(int)
            polarity_changed = Signal(scope_ivi_interface.TVTriggerPolarity)
            signal_format_changed = Signal(str)
        
            @property
            def trigger_event(self):
                """
                Specifies the event on which the oscilloscope triggers.
        
                See also: TVTriggerEvent
                """
                mapper = {'field1': scope_ivi_interface.TVTriggerEvent.FIELD1,
                          'field2': scope_ivi_interface.TVTriggerEvent.FIELD2,
                          'any_field': scope_ivi_interface.TVTriggerEvent.ANYFIELD,
                          'line_number': scope_ivi_interface.TVTriggerEvent.LINENUMBER}
                return mapper[self.root.driver.trigger.tv.trigger_event]
        
            @trigger_event.setter
            def trigger_event(self, value):
                mapper = {scope_ivi_interface.TVTriggerEvent.FIELD1: 'field1',
                          scope_ivi_interface.TVTriggerEvent.FIELD2: 'field2',
                          scope_ivi_interface.TVTriggerEvent.ANYFIELD: 'any_field',
                          scope_ivi_interface.TVTriggerEvent.LINENUMBER: 'line_number'}
                self.root.driver.trigger.tv.trigger_event = mapper[value]
                self.trigger_event_changed.emit(value)
        
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
                return self.root.driver.trigger.tv.line_number
        
            @line_number.setter
            def line_number(self, value):
                self.root.driver.trigger.tv.line_number = value
                self.line_number_changed.emit(self.root.driver.trigger.tv.line_number)
        
            @property
            def polarity(self):
                """
                Specifies the polarity of the TV signal.
        
                See also: TVTriggerPolarity
                """
                mapper = {'positive': scope_ivi_interface.TVTriggerPolarity.POSITIVE,
                          'negative': scope_ivi_interface.TVTriggerPolarity.NEGATIVE}
                return mapper[self.root.driver.trigger.tv.polarity]
        
            @polarity.setter
            def polarity(self, value):
                mapper = {scope_ivi_interface.TVTriggerPolarity.POSITIVE: 'positive',
                          scope_ivi_interface.TVTriggerPolarity.NEGATIVE: 'negative'}
                self.root.driver.trigger.tv.polarity = mapper[value]
                self.polarity_changed.emit(value)
        
            @property
            def signal_format(self):
                """
                Specifies the format of TV signal on which the oscilloscope triggers.
        
                See also: TVSignalFormat
                """
                mapper = {'ntsc': scope_ivi_interface.TVSignalFormat.NTSC,
                          'pal': scope_ivi_interface.TVSignalFormat.PAL,
                          'secam': scope_ivi_interface.TVSignalFormat.SECAM}
                return mapper[self.root.driver.trigger.tv.signal_format]
        
            @signal_format.setter
            def signal_format(self, value):
                mapper = {scope_ivi_interface.TVSignalFormat.NTSC: 'ntsc',
                          scope_ivi_interface.TVSignalFormat.PAL: 'pal',
                          scope_ivi_interface.TVSignalFormat.SECAM: 'secam'}
                self.root.driver.trigger.tv.signal_format = mapper[value]
                self.signal_format_changed.emit(self.root.driver.trigger.tv.signal_format)
        
            def configure(self, source, signal_format, event, polarity):
                """
                This function configures the oscilloscope for TV triggering. It configures
                the TV signal format, the event and the signal polarity.
        
                This function affects instrument behavior only if the trigger type is TV
                Trigger. Set the Trigger Type and Trigger Coupling before calling this
                function.
                """
                self.root.driver.trigger.tv.configure(source, signal_format, event, polarity)


class RuntTriggerExtension(scope_ivi_interface.RuntTriggerExtensionInterface):
    """
    Extension IVI methods for oscilloscopes supporting runt triggering
    """
    class trigger:
        @Namespace
        class runt(QObject,
                   scope_ivi_interface.RuntTriggerExtensionInterface.trigger.runt,
                   metaclass=QtInterfaceMetaclass):
            threshold_high_changed = Signal(float)
            threshold_low_changed = Signal(float)
            polarity_changed = Signal(scope_ivi_interface.Polarity)
        
            @property
            def threshold_high(self):
                """
                Specifies the high threshold the oscilloscope uses for runt triggering.
                The units are volts.
                """
                return self.root.driver.trigger.runt.threshold_high
        
            @threshold_high.setter
            def threshold_high(self, value):
                self.root.driver.trigger.runt.threshold_high = value
                self.threshold_high_changed.emit(self.root.driver.trigger.runt.threshold_high)
        
            @property
            def threshold_low(self):
                """
                Specifies the low threshold the oscilloscope uses for runt triggering.
                The units are volts.
                """
                return self.root.driver.trigger.runt.threshold_low
        
            @threshold_low.setter
            def threshold_low(self, value):
                self.root.driver.trigger.runt.threshold_low = value
                self.threshold_low_changed.emit(self.root.driver.trigger.runt.threshold_low)
        
            @property
            def polarity(self):
                """
                Specifies the polarity of the runt that triggers the oscilloscope.
        
                See also: Polarity
                """
                mapper = {'positive': scope_ivi_interface.Polarity.POSITIVE,
                          'negative': scope_ivi_interface.Polarity.NEGATIVE,
                          'either': scope_ivi_interface.Polarity.EITHER}
                return mapper[self.root.driver.trigger.runt.polarity]
        
            @polarity.setter
            def polarity(self, value):
                mapper = {scope_ivi_interface.Polarity.POSITIVE: 'positive',
                          scope_ivi_interface.Polarity.NEGATIVE: 'negative',
                          scope_ivi_interface.Polarity.EITHER: 'either'}
                self.root.driver.trigger.runt.polarity = mapper[value]
                self.polarity_changed.emit(value)
        
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
                self.root.driver.trigger.runt.configure(source,
                                                        threshold_low,
                                                        threshold_high,
                                                        polarity)


class WidthTriggerExtension:
    """
    Extension IVI methods for oscilloscopes supporting width triggering
    """
    class trigger:
        @Namespace
        class width(QObject,
                    scope_ivi_interface.WidthTriggerExtensionInterface.trigger.width,
                    metaclass=QtInterfaceMetaclass):
            condition_changed = Signal(scope_ivi_interface.WidthCondition)
            threshold_high_changed = Signal(float)
            threshold_low_changed = Signal(float)
            polarity_changed = Signal(scope_ivi_interface.Polarity)
        
            @property
            def condition(self):
                """
                Specifies whether a pulse that is within or outside the high and low
                thresholds triggers the oscilloscope. The end-user specifies the high and
                low thresholds with the Width High Threshold and Width Low Threshold
                attributes.
        
                See also: WidthCondition
                """
                mapper = {'within': scope_ivi_interface.WidthCondition.WITHIN,
                          'outside': scope_ivi_interface.WidthCondition.OUTSIDE}
                return mapper[self.root.driver.trigger.width.condition]
        
            @condition.setter
            def condition(self, value):
                mapper = {scope_ivi_interface.WidthCondition.WITHIN: 'within',
                          scope_ivi_interface.WidthCondition.OUTSIDE: 'outside'}
                self.root.driver.trigger.width.condition = mapper[value]
                self.condition_changed.emit(value)
        
            @property
            def threshold_high(self):
                """
                Specifies the high width threshold time. Units are seconds.
                """
                return self.root.driver.trigger.width.threshold_high
        
            @threshold_high.setter
            def threshold_high(self, value):
                self.root.driver.trigger.width.threshold_high = value
                self.threshold_high_changed.emit(self.root.driver.trigger.width.threshold_high)
        
            @property
            def threshold_low(self):
                """
                Specifies the low width threshold time. Units are seconds.
                """
                return self.root.driver.trigger.width.threshold_low
        
            @threshold_low.setter
            def threshold_low(self, value):
                self.root.driver.trigger.width.threshold_low = value
                self.threshold_low_changed.emit(self.root.driver.trigger.width.threshold_low)
        
            @property
            def polarity(self):
                """
                Specifies the polarity of the pulse that triggers the oscilloscope.
        
                See also: Polarity
                """
                mapper = {'positive': scope_ivi_interface.Polarity.POSITIVE,
                          'negative': scope_ivi_interface.Polarity.NEGATIVE,
                          'either': scope_ivi_interface.Polarity.EITHER}
                return mapper[self.root.driver.trigger.width.polarity]
        
            @polarity.setter
            def polarity(self, value):
                mapper = {scope_ivi_interface.Polarity.POSITIVE: 'positive',
                          scope_ivi_interface.Polarity.NEGATIVE: 'negative',
                          scope_ivi_interface.Polarity.EITHER: 'either'}
                self.root.driver.trigger.width.polarity = mapper[value]
                self.polarity_changed.emit(value)
        
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
                self.root.driver.trigger.width.configure(source,
                                                         level,
                                                         threshold_low,
                                                         threshold_high,
                                                         polarity,
                                                         condition)


class GlitchTriggerExtension(scope_ivi_interface.GlitchTriggerExtensionInterface):
    """
    Extension IVI methods for oscilloscopes supporting glitch triggering
    """
    class trigger:
        @Namespace
        class glitch(QObject,
                     scope_ivi_interface.GlitchTriggerExtensionInterface.trigger.glitch,
                     metaclass=QtInterfaceMetaclass):
            condition_changed = Signal(scope_ivi_interface.GlitchCondition)
            polarity_changed = Signal(scope_ivi_interface.Polarity)
            width_changed = Signal(float)
        
            @property
            def condition(self):
                """
                Specifies the glitch condition. This attribute determines whether the
                glitch trigger happens when the oscilloscope detects a pulse with a
                width less than or greater than the width value.
        
                See also: GlitchCondition
                """
                mapper = {'greater_than': scope_ivi_interface.GlitchCondition.GREATER_THAN,
                          'less_than': scope_ivi_interface.GlitchCondition.LESS_THAN}
                return mapper[self.root.driver.trigger.glitch.condition]
        
            @condition.setter
            def condition(self, value):
                mapper = {scope_ivi_interface.GlitchCondition.GREATER_THAN: 'greater_than',
                          scope_ivi_interface.GlitchCondition.LESS_THAN: 'less_than'}
                self.root.driver.trigger.glitch.condition = mapper[value]
                self.condition_changed.emit(value)
        
            @property
            def polarity(self):
                """
                Specifies the polarity of the glitch that triggers the oscilloscope.
        
                See also: Polarity
                """
                mapper = {'positive': scope_ivi_interface.Polarity.POSITIVE,
                          'negative': scope_ivi_interface.Polarity.NEGATIVE,
                          'either': scope_ivi_interface.Polarity.EITHER}
                return mapper[self.root.driver.trigger.glitch.polarity]
        
            @polarity.setter
            def polarity(self, value):
                mapper = {scope_ivi_interface.Polarity.POSITIVE: 'positive',
                          scope_ivi_interface.Polarity.NEGATIVE: 'negative',
                          scope_ivi_interface.Polarity.EITHER: 'either'}
                self.root.driver.trigger.glitch.polarity = mapper[value]
                self.polarity_changed.emit(value)
        
            @property
            def width(self):
                """
                Specifies the glitch width. The units are seconds. The oscilloscope
                triggers when it detects a pulse with a width less than or greater than
                this value, depending on the Glitch Condition attribute.
                """
                return self.root.driver.trigger.glitch.width
        
            @width.setter
            def width(self, value):
                self.root.driver.trigger.glitch.width = value
                self.condition_changed.emit(self.root.driver.trigger.glitch.width)
        
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
                self.root.driver.trigger.glitch.configure(source, level, width, polarity, condition)


class AcLineTriggerExtension(scope_ivi_interface.AcLineTriggerExtensionInterface):
    """
    Extension IVI methods for oscilloscopes supporting AC line triggering
    """
    class trigger:
        @Namespace
        class ac_line(QObject,
                      scope_ivi_interface.AcLineTriggerExtensionInterface.trigger.ac_line,
                      metaclass=QtInterfaceMetaclass):
            slope_changed = Signal(scope_ivi_interface.ACLineSlope)
        
            @property
            def slope(self):
                """
                Specifies the slope of the zero crossing upon which the scope triggers.
        
                See also: ACLineSlope
                """
                mapper = {'positive': scope_ivi_interface.ACLineSlope.POSITIVE,
                          'negative': scope_ivi_interface.ACLineSlope.NEGATIVE,
                          'either': scope_ivi_interface.ACLineSlope.EITHER}
                return mapper[self.root.driver.trigger.ac_line.slope]
        
            @slope.setter
            def slope(self, value):
                mapper = {scope_ivi_interface.ACLineSlope.POSITIVE: 'positive',
                          scope_ivi_interface.ACLineSlope.NEGATIVE: 'negative',
                          scope_ivi_interface.ACLineSlope.EITHER: 'either'}
                self.root.driver.trigger.ac_line.slope = mapper[value]
                self.slope_changed.emit(value)


class ProbeAutoSenseExtension(scope_ivi_interface.ProbeAutoSenseExtensionInterface):
    """
    Extension IVI methods for oscilloscopes supporting probe attenuation sensing
    """
    class channels(scope_ivi_interface.ProbeAutoSenseExtensionInterface.channels):
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
            return self.root.driver.channels[self.index].probe_attenuation_auto
    
        @probe_attenuation_auto.setter
        def probe_attenuation_auto(self, value):
            self.root.driver.channels[self.index].probe_attenuation_auto = value
            self.probe_attenuation_auto_changed.emit(
                self.root.driver.channels[self.index].probe_attenuation_auto)


class ContinuousAcquisitionExtension(scope_ivi_interface.ContinuousAcquisitionExtensionInterface):
    """
    The IviScopeContinuousAcquisition extension group provides support for oscilloscopes that can
    perform a continuous acquisition.
    """
    class trigger(scope_ivi_interface.ContinuousAcquisitionExtensionInterface.trigger):
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
            return self.root.driver.trigger.continuous

        @continuous.setter
        def continuous(self, value):
            self.root.driver.trigger.continuous = value
            self.continuous_changed.emit(value)


class AverageAcquisitionExtension(scope_ivi_interface.AverageAcquisitionExtensionInterface):
    """
    The IviScopeAverageAcquisition extension group provides support for oscilloscopes that can
    perform the average acquisition.
    """
    class acquisition(scope_ivi_interface.AverageAcquisitionExtensionInterface.acquisition):
        number_of_averages_changed = Signal(int)
    
        @property
        def number_of_averages(self):
            """
            Specifies the number of waveform the oscilloscope acquires and averages. After the
            oscilloscope acquires as many waveforms as this attribute specifies, it returns to the
            idle state. This attribute affects instrument behavior only when the Acquisition Type
            attribute is set to Average.
            """
            return self.root.driver.acquisition.number_of_averages
    
        @number_of_averages.setter
        def number_of_averages(self, value):
            self.root.driver.acquisition.number_of_averages = value
            self.number_of_averages_changed.emit(value)


class SampleModeExtension(scope_ivi_interface.SampleModeExtensionInterface):
    """
    Extension IVI methods for oscilloscopes supporting equivalent and real time acquisition
    """
    class acquisition(scope_ivi_interface.SampleModeExtensionInterface.acquisition):
        sample_mode_changed = Signal(scope_ivi_interface.SampleMode)
    
        @property
        def sample_mode(self):
            """
            Returns the sample mode the oscilloscope is currently using.
    
            See also: SampleMode
            """
            mapper = {'real_time': scope_ivi_interface.SampleMode.REAL_TIME,
                      'equivalent_time': scope_ivi_interface.SampleMode.EQUIVALENT_TIME}
            return mapper[self.root.driver.acquisition.sample_mode]
    
        @sample_mode.setter
        def sample_mode(self, value):
            mapper = {scope_ivi_interface.SampleMode.REAL_TIME: 'real_time',
                      scope_ivi_interface.SampleMode.EQUIVALENT_TIME: 'equivalent_time'}
            self.root.driver.acquisition.sample_mode = mapper[value]
            self.sample_mode_changed.emit(value)


class TriggerModifierExtension(scope_ivi_interface.TriggerModifierExtensionInterface):
    """
    Extension IVI methods for oscilloscopes supporting specific triggering subsystem behavior in 
    the absence of a trigger
    """
    class trigger(scope_ivi_interface.TriggerModifierExtensionInterface.trigger):
        modifier_changed = Signal(scope_ivi_interface.TriggerModifier)
    
        @property
        def modifier(self):
            """
            Specifies the trigger modifier. The trigger modifier determines the
            oscilloscope's behavior in the absence of the configured trigger.
    
            See also: TriggerModifier
            """
            mapper = {'none': scope_ivi_interface.TriggerModifier.NONE,
                      'auto': scope_ivi_interface.TriggerModifier.AUTO,
                      'auto_level': scope_ivi_interface.TriggerModifier.AUTO_LEVEL}
            return mapper[self.root.driver.trigger.modifier]
    
        @modifier.setter
        def modifier(self, value):
            mapper = {scope_ivi_interface.TriggerModifier.NONE: 'none',
                      scope_ivi_interface.TriggerModifier.AUTO: 'auto',
                      scope_ivi_interface.TriggerModifier.AUTO_LEVEL: 'auto_level'}
            self.root.driver.trigger.modifier = mapper[value]
            self.modifier_changed.emit(value)


class AutoSetupExtension(scope_ivi_interface.AutoSetupExtensionInterface):
    """
    The IviScopeAutoSetup extension group provides support for oscilloscopes that can perform an
    auto-setup operation.
    """
    class measurement(scope_ivi_interface.AutoSetupExtensionInterface.measurement):
        def auto_setup(self):
            """
            This function performs an auto-setup on the instrument.
            """
            self.root.driver.measurement.auto_setup()


class WaveformMeasurementExtension(scope_ivi_interface.WaveformMeasurementExtensionInterface):
    """
    Extension IVI methods for oscilloscopes supporting waveform measurements
    """
    class reference_level(
        QObject,
        scope_ivi_interface.WaveformMeasurementExtensionInterface.reference_level,
        metaclass=QtInterfaceMetaclass):

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
            return self.root.driver.reference_level.high
    
        @high.setter
        def high(self, value):
            self.root.driver.reference_level.high = value
            self.high_changed.emit(self.root.driver.reference_level.high)
    
        @property
        def middle(self):
            """
            Specifies the middle reference the oscilloscope uses for waveform
            measurements. The value is a percentage of the difference between the
            Voltage High and Voltage Low.
            """
            return self.root.driver.reference_level.middle
    
        @middle.setter
        def middle(self, value):
            self.root.driver.reference_level.middle = value
            self.middle_changed.emit(self.root.driver.reference_level.middle)
    
        @property
        def low(self):
            """
            Specifies the low reference the oscilloscope uses for waveform
            measurements. The value is a percentage of the difference between the
            Voltage High and Voltage Low.
            """
            return self.root.driver.reference_level.low
    
        @low.setter
        def low(self, value):
            self.root.driver.reference_level.low = value
            self.low_changed.emit(self.root.driver.reference_level.low)
    
        def configure(self, low, middle, high):
            """
            This function configures the reference levels for waveform measurements.
            Call this function before calling the Read Waveform Measurement or Fetch
            Waveform Measurement to take waveform measurements.
            """
            self.root.driver.reference_level.configure(low, middle, high)

    class channels:
        class measurement(
            scope_ivi_interface.WaveformMeasurementExtensionInterface.channels.measurement):
            """
            Extension IVI methods for oscilloscopes supporting waveform measurements
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
        
                See also: MeasurementFunction
                """
                mapper = {scope_ivi_interface.MeasurementFunction.RISE_TIME: 'rise_time',
                          scope_ivi_interface.MeasurementFunction.FALL_TIME: 'fall_time',
                          scope_ivi_interface.MeasurementFunction.FREQUENCY: 'frequency',
                          scope_ivi_interface.MeasurementFunction.PERIOD: 'period',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_RMS: 'voltage_rms',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_PEAK_TO_PEAK: 'voltage_peak_to_peak',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_MAX: 'voltage_max',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_MIN: 'voltage_min',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_HIGH: 'voltage_high',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_LOW: 'voltage_low',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_AVERAGE: 'voltage_average',
                          scope_ivi_interface.MeasurementFunction.WIDTH_NEGATIVE: 'width_negative',
                          scope_ivi_interface.MeasurementFunction.WIDTH_POSITIVE: 'width_positive',
                          scope_ivi_interface.MeasurementFunction.DUTY_CYCLE_NEGATIVE: 'duty_cycle_negative',
                          scope_ivi_interface.MeasurementFunction.DUTY_CYCLE_POSITIVE: 'duty_cycle_positive',
                          scope_ivi_interface.MeasurementFunction.AMPLITUDE: 'amplitude',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_CYCLE_RMS: 'voltage_cycle_rms',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_CYCLE_AVERAGE: 'voltage_cycle_average',
                          scope_ivi_interface.MeasurementFunction.OVERSHOOT: 'overshoot',
                          scope_ivi_interface.MeasurementFunction.PRESHOOT: 'preshoot'}
                return self.root.driver.channels[self.parent_namespace.index].measurement.fetch_waveform_measurement(
                    mapper[measurement_function])
        
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

                See also: MeasurementFunction
                """
                mapper = {scope_ivi_interface.MeasurementFunction.RISE_TIME: 'rise_time',
                          scope_ivi_interface.MeasurementFunction.FALL_TIME: 'fall_time',
                          scope_ivi_interface.MeasurementFunction.FREQUENCY: 'frequency',
                          scope_ivi_interface.MeasurementFunction.PERIOD: 'period',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_RMS: 'voltage_rms',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_PEAK_TO_PEAK: 'voltage_peak_to_peak',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_MAX: 'voltage_max',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_MIN: 'voltage_min',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_HIGH: 'voltage_high',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_LOW: 'voltage_low',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_AVERAGE: 'voltage_average',
                          scope_ivi_interface.MeasurementFunction.WIDTH_NEGATIVE: 'width_negative',
                          scope_ivi_interface.MeasurementFunction.WIDTH_POSITIVE: 'width_positive',
                          scope_ivi_interface.MeasurementFunction.DUTY_CYCLE_NEGATIVE: 'duty_cycle_negative',
                          scope_ivi_interface.MeasurementFunction.DUTY_CYCLE_POSITIVE: 'duty_cycle_positive',
                          scope_ivi_interface.MeasurementFunction.AMPLITUDE: 'amplitude',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_CYCLE_RMS: 'voltage_cycle_rms',
                          scope_ivi_interface.MeasurementFunction.VOLTAGE_CYCLE_AVERAGE: 'voltage_cycle_average',
                          scope_ivi_interface.MeasurementFunction.OVERSHOOT: 'overshoot',
                          scope_ivi_interface.MeasurementFunction.PRESHOOT: 'preshoot'}
                return self.root.driver.channels[
                    self.parent_namespace.index].measurement.read_waveform_measurement(mapper[measurement_function],
                                                                                       maximum_time)


class MinMaxWaveformExtension(scope_ivi_interface.MinMaxWaveformExtensionInterface):
    """
    Extension IVI methods for oscilloscopes supporting minimum and maximum waveform acquisition
    """
    class acquisition(scope_ivi_interface.MinMaxWaveformExtensionInterface.acquisition):
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
            return self.root.driver.acquisition.number_of_envelopes
    
        @number_of_envelopes.setter
        def number_of_envelopes(self, value):
            self.root.driver.acquisition.number_of_envelopes = value
            self.number_of_envelopes_changed.emit(value)
    
    class channels(scope_ivi_interface.MinMaxWaveformExtensionInterface.channels):
        class measurement(
            scope_ivi_interface.MinMaxWaveformExtensionInterface.channels.measurement):
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
                return self.root.driver.channels[
                    self.parent_namespace.index].measurement.fetch_waveform_min_max()

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
                return self.root.driver.channels[
                    self.parent_namespace.index].measurement.read_waveform_min_max()


class PythonIviScope(PythonIviBase, _Scope):
    """
    Module for accessing oscilloscopes via PythonIVI library.

    Config options:
    - driver : str module.class name of driver within the python IVI library
                   e.g. 'ivi.agilent.agilentDSOS204A.agilentDSOS204A'
    - uri : str unique remote identifier used to connect to instrument.
                e.g. 'TCPIP0::192.168.1.1::hislip0::INSTR'
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
        this enables settings data from dynamic descriptors

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
        driver_capabilities = inspect.getmro(type(self.driver))

        # dynamic class generator
        class IviAcquisitionMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.scope.Interpolation in driver_capabilities:
                    bases += (InterpolationExtension.acquisition, )
                if ivi.scope.AverageAcquisition in driver_capabilities:
                    bases += (AverageAcquisitionExtension.acquisition, )
                if ivi.scope.MinMaxWaveform in driver_capabilities:
                    bases += (MinMaxWaveformExtension.acquisition, )
                if ivi.scope.SampleMode in driver_capabilities:
                    bases += (SampleModeExtension.acquisition, )
                return super().__new__(mcs, name, bases, attrs)

        class IviAcquisition(_Scope.acquisition, metaclass=IviAcquisitionMetaclass):
            pass

        self.acquisition = Namespace(IviAcquisition)

        # dynamic measurement class generator
        class IviMeasurementMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.scope.AutoSetup in driver_capabilities:
                    bases += (AutoSetupExtension.measurement, )
                return super().__new__(mcs, name, bases, attrs)

        class IviMeasurement(_Scope.measurement, metaclass=IviMeasurementMetaclass):
            pass

        self.measurement = Namespace(IviMeasurement)

        # dynamic trigger class generator
        class IviTriggerMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.scope.TVTrigger in driver_capabilities:
                    bases += (TVTriggerExtension.trigger, )
                if ivi.scope.RuntTrigger in driver_capabilities:
                    bases += (RuntTriggerExtension.trigger, )
                if ivi.scope.GlitchTrigger in driver_capabilities:
                    bases += (GlitchTriggerExtension.trigger, )
                if ivi.scope.WidthTrigger in driver_capabilities:
                    bases += (WidthTriggerExtension.trigger, )
                if ivi.scope.AcLineTrigger in driver_capabilities:
                    bases += (AcLineTriggerExtension.trigger, )
                if ivi.scope.ContinuousAcquisition in driver_capabilities:
                    bases += (ContinuousAcquisitionExtension.trigger, )
                if ivi.scope.TriggerModifier in driver_capabilities:
                    bases += (TriggerModifierExtension.trigger, )
                return super().__new__(mcs, name, bases, attrs)

        class IviTrigger(_Scope.trigger, metaclass=IviTriggerMetaclass):
            pass

        self.trigger = Namespace(IviTrigger)

        class IviChannelMeasurementMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.scope.WaveformMeasurement in driver_capabilities:
                    bases += (WaveformMeasurementExtension.channels.measurement, )
                if ivi.scope.MinMaxWaveform in driver_capabilities:
                    bases += (MinMaxWaveformExtension.channels.measurement, )
                return super().__new__(mcs, name, bases, attrs)

        class IviChannelMeasurement(_Scope.channels.measurement,
                                    metaclass=IviChannelMeasurementMetaclass):
            pass

        class IviChannelMetaclass(QtInterfaceMetaclass):
            def __new__(mcs, name, bases, attrs):
                if ivi.scope.ProbeAutoSense in driver_capabilities:
                    bases += (ProbeAutoSenseExtension.channels, )
                return super().__new__(mcs, name, bases, attrs)

        class IviChannel(_Scope.channels, metaclass=IviChannelMetaclass):
            measurement = Namespace(IviChannelMeasurement)

        self.channels = Namespace.repeat(self.driver._channel_count)(IviChannel)

        if ivi.scope.WaveformMeasurement in driver_capabilities:
            self.reference_level = Namespace(WaveformMeasurementExtension.reference_level)