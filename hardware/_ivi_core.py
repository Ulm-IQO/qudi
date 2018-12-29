"""
This file contains the basic functionality used by instrument drivers based on the
IVI interfaces.

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


# region Namespace
class Namespace:
    """
    The namespace decorator can be used to automatically instantiate inner classes.

    Inner classes are used to group functionality. The namespace decorator simplifies their use and provides some
    useful auxilliary attributes.


    Example:
    ========

    class Scope(SomeBaseClass):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._channel_count = 4

    @Namespace
    class measurement:
        @property
        def status(self):
            return self.root.send_command('status')

    @Namespace
    class acquisition:
        def start(self):
            self.root.send_command('acquisition:start')

    @Namespace
    class trigger:
        @Namespace
        class edge:
            @property
            def level(self):
                return self.root.send_command('trigger:edge:level?')

            @level.setter
            def level(self, value):
                self.root.send_command('trigger:edge:level {0}'.format(value))

    @Namespace.repeat('_channel_count')
    class channels:
        @property
        def offset(self):
            return self.root.send_command('channel{0}:offset?'.format(self.index))

        @offset.setter
        def offset(self, value):
            self.root.send_command('channel{0}:offset {1}'.format(self.index, value))
    """

    def __init__(self, cls):
        self.cls = cls

    def __get__(self, instance, owner):
        if not instance:
            return self.cls

        name = self.cls.__name__ + 'cached'

        # if we are already cached, use this version
        if name in instance.__dict__:
            return instance.__dict__[name]

        # create instance
        namespace = self.cls()
        # parent
        namespace.parent_namespace = instance
        # find root, root has no root attribute
        namespace.root = instance
        while hasattr(namespace.root, 'root'):
            namespace.root = namespace.root.root
        setattr(instance, name, namespace)
        return namespace

    @classmethod
    def repeat(cls, count, container=None):
        """
        Decorator used for IVI repeated capabilities.

        :param count: how often the capability shall be repeated.
        :param container:
        """
        class NamespaceRepeat:
            def __init__(self, cls):
                self.cls = cls
                self.count = count
                self.container = container

            def __get__(self, instance, owner):
                if not instance:
                    return self.cls

                name = self.cls.__name__ + 'cached'

                # if we are already cached, use this version
                if name in instance.__dict__:
                    return instance.__dict__[name]

                # find root, root has no root attribute
                root = instance
                while hasattr(root, 'root'):
                    root = root.root

                # determine number of instances
                # if it is a string, check namespace container instance first, then root
                if isinstance(self.count, int):
                    if self.count <= 0:
                        raise Exception('Invalid value for count: {0}.'.format(self.count))
                elif isinstance(self.count, str):
                    value = getattr(instance, self.count, None)
                    if value is None:
                        value = getattr(root, self.count, 1)
                    self.count = value
                else:
                    raise Exception('Invalid value for count: {0}.'.format(self.count))

                # create instances
                if self.container is None:
                    namespaces = []
                else:
                    namespaces = self.container
                for ii in range(self.count):
                    obj = self.cls()
                    obj.parent_namespace = instance
                    obj.root = root
                    obj.index = ii
                    namespaces.append(obj)
                setattr(instance, name, namespaces)
                return namespaces

        return NamespaceRepeat
# endregion


# region Exceptions
class ConfigurationServerException(Exception):
    """
    An error occurred while using the Configuration Server.

    When accessing the IVI-COM Configuration Server using the primary interop assembly (PIA), this
    exception is used to relay an exception thrown by the configuration server PIA (for example, an
    Unauthorized Access exception or an IO exception). The exception thrown by the Configuration Server is
    the inner exception for this one.
    When accessing the IVI-COM or IVI-C Configuration Server using other forms of interop, this exception is
    used to relay the error return code reported by the Configuration Server.
    """


class FileFormatException(Exception):
    """
    A file does not conform to it’s expected format.

    If the driver catches an exception that prompted this exception (for example, a system File Not Found
    exception), that exception should be made the inner exception for this one.
    """


class IdQueryFailedException(Exception):
    """
    The instrument ID query failed.

    Under normal circumstances, an ID query is done once, either up-front in the constructor, or in the first get
    for a property that returns ID Query information. Class compliant properties that potentially return ID
    query information are InstrumentManufacturer, InstrumentModel, and InstrumentFirmwareRevision, which
    are all in the IiviDriverIdentity interface. Instrument specific properties, such as a property that returns
    serial number, may also do an ID query.
    """


class InstrumentStatusException(Exception):
    """
    The driver detected an instrument error.

    Avoid using this exception to relay another exception. As a general rule, just let the original exception
    propagate up.
    """


class InvalidOptionValueException(Exception):
    """
    An invalid value is assigned to an option.

    Since the driver is required to process option strings in the constructor, this exception shall only be thrown
    from the constructor.
    """


class IOException(Exception):
    """
    A call to the underlying I/O mechanism being used by the driver to communicate with the instrument has failed.

    When accessing .NET I/O libraries or COM I/O libraries using a primary interop assembly (PIA), this exception may
    be used to relay an exception thrown by the I/O library. The exception thrown by the I/O library is the inner
    exception for this one.

    When accessing a native C or COM I/O library using other forms of interop, this exception may be used to relay the
    error return code reported by the Configuration Server. If the underlying I/O library reports a timeout, use
    the IOTimeoutException.
    """


class IOTimeoutException(Exception):
    """
    A call to the underlying IO mechanism being used by the driver to communicate with the instrument has timed out.
    """


class IviCInteropException(Exception):
    """
    When an underlying IVI-C driver was called to perform an action, the IVI-C driver action did not succeed.
    """


class MaxTimeExceededException(Exception):
    """
    The operation implemented by the method did not complete within the maximum time allowed.

    Use this exception, rather than the IOTimeoutException, whenever a method includes a parameter (for
    example, maximumTime) that specifies maximum time allowed for the method’s operation to complete.
    """


class OperationNotSupportedException(Exception):
    """
    A driver feature (for this exception, a method, property, or event) is not supported by the driver.

    This exception should not be used for parameters. Use ValueNotSupportedException for enumeration
    values or discrete values from a list of defined values that aren’t supported by the driver, and
    OutOfRangeException for other invalid values.

    This exception should not be used for the Reset method. Use ResetNotSupportedException if the
    instrument does not support resets.
    """


class OperationPendingException(Exception):
    """
    An operation is in progress that prevents the method or property from being executed.
    """


class OptionMissingException(Exception):
    """
    A required option is missing from the option string.

    Since the driver is required to process option strings in the constructor, this exception shall only be thrown
    from the constructor.
    """


class OptionStringFormatException(Exception):
    """
    The driver cannot parse the option string.

    Since the driver is required to process option strings in the constructor, this exception shall only be thrown
    from the constructor.
    """


class OutOfRangeException(Exception):
    """
    The driver detected an argument whose value is out or range.

    Use this exception only if a more specific exception is not appropriate.
    """


class ResetFailedException(Exception):
    """
    Raised if reset failed.

    Under normal circumstances, an instrument reset is done in the constructor and in the utility.reset() and
    utility.reset_with_defaults() methods. For particular drivers, other properties and methods may include a reset
    if needed for some instrument specific reason.
    """


class ResetNotSupportedException(Exception):
    """
    The instrument does not support the reset operation.

    If the instrument is capable of doing a reset, but the reset fails, use the Reset Failed exception.
    """


class SimulationStateException(Exception):
    """
    Raised if the simulation state cannot be changed.

    After construction, the simulation property cannot be set to false, only to true. Some drivers may not allow
    simulation to be changed at all.
    """


class TriggerNotSoftwareException(Exception):
    """
    A Send Software Trigger method could not send a software trigger.

    This exception should only be thrown by send_software_trigger() methods as defined in Section 2, Software
    Triggering Capability, of IVI-3.3, Cross Class Capability Specification.
    """


class UnexpectedResponseException(Exception):
    """
    The driver received an unexpected response from the instrument.
    """


class UnknownOptionException(Exception):
    """
    The option string contains an option name that it does not recognize.

    Since the driver is required to process option strings in the constructor, this exception shall only be thrown
    from the constructor.
    """


class UnknownPhysicalNameException(Exception):
    """
    Raised if physical name does not exist.

    When establishing the map from virtual repeated capability names to physical repeated capability names, a
    physical name did not exist.

    This exception also applies in cases where any member of a virtual range mapped to a physical name that
    did not exist.

    Since the driver is required to read all relevant configuration store information in the constructor, this
    exception shall only be thrown by the constructor.
    """


class ValueNotSupportedException(Exception):
    """
    An enumerated value or a discrete value from a list of defined values is not supported by the specific driver.

    Drivers should use OutOfRangeException when they encounter other types of invalid values.
    """


#endregion
