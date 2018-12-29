# -*- coding: utf-8 -*-
"""
This file contains the base class for all pyivi library interfaces.

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

from core.module import Base, ConfigOption
from core.util.interfaces import InterfaceMetaclass
from interface.ivi.inherent_capabilities_interface import InherentCapabilitiesInterface
from qtpy.QtCore import QObject
from qtpy.QtCore import Signal
import abc
import pyivi
from ._ivi_core import Namespace


class QtInterfaceMetaclass(type(QObject), abc.ABCMeta):
    pass


class PyIviBase(Base, InherentCapabilitiesInterface, metaclass=InterfaceMetaclass):
    """
    Base class for connecting to hardware via pyivi library.

    Config options:

    - uri : str Unique remote identifier used to connect to instrument.
                e.g. 'TCPIP::192.168.1.1::INSTR'
    - model : str Specifies the instrument model.
                  default value: None. Pyivi uses VISA to determine the model. Specifying the model with simulate=True
                  prevents instrument connections.
    - flavour : str Specifies which ivi interface shall be used. 'IVI-COM' and 'IVI-C' are supported.
                    default value: 'IVI-COM'
    - simulate : bool Specifies whether the driver simulates I/O operations
                      default value: False

    Example:

    dsos204a_pyivi:
        module.Class: 'scope.pyivi_scope.PyIviScope'
        uri: 'TCPIP::192.168.1.1::INSTR'
    """

    # configuration options
    uri = ConfigOption('uri', missing='error')
    model = ConfigOption('model', default=None)
    flavour = ConfigOption('flavour', default='IVI-COM')
    simulate = ConfigOption('simulate', default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.driver = None

    def on_activate(self):
        """
        Event handler called when module is activated.

        Opens connection to instrument.
        """
        # instantiate class and connect to scope
        self.driver = pyivi.ivi_instrument(self.uri, model=self.model, flavour=self.flavour, simulate=self.simulate)

    def on_deactivate(self):
        """
        Event handler called when module is deactivated.

        Closes connection to instrument.
        """
        if self.driver is not None:
            del self.driver
            self.driver = None

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
