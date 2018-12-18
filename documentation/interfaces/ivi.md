# Interface for instruments based on IVI specifications

## Introduction
The IVI foundation has defined a set of standard interfaces for instruments to allow for simple
interchangeability. While the interfaces are defined for C and .NET and no official python
interfaces are defined, we mainly follow the recommendations of the specifications for .NET.

The IVI interface specifications can be found at the following locations:

- [Oscilloscopes - scope](http://www.ivifoundation.org/downloads/Class%20Specifications/IVI-4.1_Scope_2016-10-14.pdf)
- [Function Generators - fgen](http://www.ivifoundation.org/downloads/Class%20Specifications/IVI-4.3_Fgen_2016-10-14.pdf)

## Example usage

Here we implement an oscilloscope which has an AC line trigger.

```python
from interface.ivi.scope_interface import ScopeIviInterface
from interface.ivi.scope_interface import AcLineTriggerExtensionInterface
from hardware._ivi_core import Namespace


class Scope(ScopeIviInterface, AcLineTriggerExtensionInterface):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._channel_count = 4

    def send_command(self, s):
        # send command to device

    @Namespace
    class acquisition(ScopeIviInterface.acquision):
        def configure_record(self, time_per_record, minimum_number_of_points, acquisition_start_time):
            self.root.send_command('time_per_record {0}'.format(time_per_record)
            # ...

        # ...


    @Namespace
    class measurement(ScopeIviInterface.measurement):
        @property
        def status(self):
            return self.root.send_command('status')

        # ...


    @Namespace
    class trigger:
        @Namespace
        class edge(ScopeIviInterface.trigger.edge):
            @property
            def level(self):
                return self.root.send_command('trigger:edge:level?')

            @level.setter
            def level(self, value):
                self.root.send_command('trigger:edge:level {0}'.format(value))

        # this is the AcLineTrigger extension
        @Namespace
        class ac_line(AcLineTriggerExtensionInterface.trigger.ac_line):
            @property
            def slope(self):
                return self.root.get_command('trigger:acline:slope?")

            @slope.setter
            def slope(self, value):
                self.root.send_command('trigger:acline:slope {0}'.format(value))
        # and here it ends

    # Instruments have multiple channels. With the repeat option of Namespace we can have a list
    # of channels.
    @Namespace.repeat('_channel_count')
    class channels(ScopeIviInterface.channels):
        @property
        def offset(self):
            return self.root.send_command('channel{0}:offset?'.format(self.index))

        @offset.setter
        def offset(self, value):
            self.root.send_command('channel{0}:offset {1}'.format(self.index, value))

        # ...
```


## Namespace

The namespace decorator is defined in `hardware._ivi_core`. Namespaces help to implement the ivi interface. A Namespace is a subclass which when accessed
the first time automatically is instanciated. No manual instanciating is necessary. Namespaces
can be nested. A namespace has two useful properties:

- `root`: Returns the first parent class which is not a Namespace. This is most often used to
          access the module itself.
- `parent_namespace`: Returns the parent namespace.

Sometimes a namespace should be available multiple times. An example are the channels of an
instrument. Using `@Namespace.repeat(count)` a namespace will be repeated count times in a list.
Please see the channels namespace in the example above.

## Supported Python Instrument Libraries

### Python IVI

`python ivi` is a collection of instrument drivers written in python following the IVI interface
specifications. The library can be found [here](https://github.com/python-ivi/python-ivi). We
suggest to use our [fork](https://github.com/qpit/python-ivi) as it contains several additional
drivers and fixes for oscilloscopes.

The Qudi wrappers for python IVI can be found in

- scope: `hardware.scope.python_ivi_scope`
- fgen: `hardware.fgen.python_ivi_fgen`

##### Configuration options

- `driver`: `str` module.class name of driver within the python IVI library,
                  e.g. 'ivi.tektronix.tektronixAWG5000.tektronixAWG5002c'
- `uri`: `str` str unique remote identifier used to connect to instrument,
               e.g. 'TCPIP::192.168.1.1::INSTR'