# How to create hardware modules satisfying multiple interfaces {#multiple_interface_hardware}

This article will describe the qudi feature to "overload" interface methods within hardware modules 
in case of namespace collisions between multiple inherited interface classes.

## Why do we even need this feature?
Imagine you have an interface class `DataReader` which interfaces a simple data reader device.
You also have another interface class `DataOutput` which interfaces a simple data output device.
Now let's say you have a piece of hardware that can handle both tasks simultaneously and you want 
to write a hardware module for that.

First of all you would need to inherit both interfaces in the class definition of your hardware 
module as well as the base class for all qudi modules. Please note that `Base` always must be first: 
```python
from core.module import Base
from interface.data_reader import DataReader
from interface.data_output import DataOutput

class MyHardwareModule(Base, DataReader, DataOutput):
    """
    This will become my new fancy hardware module to combine DataReader and DataOutput functionality
    """
    pass
```

So far so good...
Now let's have a closer look at the class members of `DataReader` and `DataOutput`:
```python
from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class DataReader(metaclass=InterfaceMetaclass):
    """
    This is a fictional data reader interface.
    """

    @abstract_interface_method
    def get_data(self):
        """
        Get the read data array.

        @return list: Data array
        """
        pass

    @abstract_interface_method
    def start(self):
        """
        Start the data acquisition.

        @return int: error code (0:OK, -1:error)
        """
        pass


class DataOutput(metaclass=InterfaceMetaclass):
    """
    This is a fictional data output interface.
    """

    @abstract_interface_method
    def set_data(self, data):
        """
        Set the data array to output.

        @param list data: The data array to output
        @return int: error code (0:OK, -1:error)
        """
        pass

    @abstract_interface_method
    def start(self):
        """
        Start the data output.

        @return int: error code (0:OK, -1:error)
        """
        pass
```

As you can see it will be no problem to just implement the `get_data` and `set_data` methods in our 
new hardware module since they have unique names that are just present in a single interface, 
respectively.
The method `start` however is an entirely different story. In a traditional way you can only define 
one method with that name in your hardware module, thus preventing to start each task separately.
And this is where the ominous `@abstract_interface_method` decorator comes into play.

## How to "overload" an interface method
The decorator `@abstract_interface_method` has two purposes. 

One is to make the decorated method an 
_abstractmethod_ (see [_abc_](https://docs.python.org/3/library/abc.html) module for more information), so that Python will raise an exception 
upon import if your derived hardware module does not implement this method.

The other functionality enables you to "overload" the decorated method inside your derived hardware module.

Let's look at an example on how this can be used in a hardware module based on the example classes 
presented in the previous section:
```python
from core.module import Base
from interface.data_reader import DataReader
from interface.data_output import DataOutput

class MyHardwareModule(Base, DataReader, DataOutput):
    """
    This will become my new fancy hardware module to combine DataReader and DataOutput functionality
    """
    # Define __init__ and qudi module activation/deactivation
    
    # Do other stuff

    def get_data(self):
        # Do something
        return list(range(42))

    def set_data(self, data):
        # Do something
        return 0

    @DataReader.start.register('DataReader')
    def start_read(self):
        # Start the data reader
        print('Data reader started through "DataReader" interface method')
        return 0
    
    @DataOutput.start.register('DataOutput')
    def start_output(self):
        # Start the data output
        print('Data output started through "DataOutput" interface method')
        return 0
```

As already mentioned, `set_data` and `get_data` do not need special treatment.

Through the decorator used here, the two methods `start_read` and `start_output` will both be 
registered to the interface method `start`; each one associated to a different interface class name 
('DataReader' or 'DataOutput').

The interface class name is used as a keyword to select which implementation of `start` to call:
```python
<MyHardwareModule>.start['DataReader']()  # Will call <MyHardwareModule>.start_read()
<MyHardwareModule>.start['DataOutput']()  # Will call <MyHardwareModule>.start_output()
```

So when calling overloaded methods of a hardware class directly, you can select which 
implementation to call by adding the respective interface class name in square brackets after the 
method name.

If no methods have been registered on `start` and `start` is not overwritten by the hardware 
module class definition, calling it will throw `NotImplementedError`.
Using keywords that have not been registered will result in `KeyError`.

You can however always overwrite the interface method in your hardware class as usual by just 
defining a regular method (without the decorator) if you do not need to overload it.

## Interface methods and logic module Connector
Now you might think this new way of calling overloaded interface methods will not work with logic 
modules since the logic would need to know how to formulate the method call.

In order to work around this issue the `Connector` object is your best friend. 
During instantiation of a `Connector` object the logic module passes the interface class name as 
parameter. As such the `Connector` instance can provide a hardware module proxy when called to 
hide the overload mechanics of interface methods from the logic module. 

To illustrate this further, let's assume you have a logic module `MyLogicModule` which is 
interfacing `DataReader` and `DataOutput` through our new hardware module `MyHardwareModule`.
A call to each different `start` method qould look like:
```python
from core.connector import Connector
from logic.generic_logic import GenericLogic

class MyLogicModule(GenericLogic):
    """ 
    Fictional logic module illustrating the use of the Connector object with overloaded 
    interface methods.
    """
    # Instantiate connectors    
    data_reader = Connector(interface='DataReader')
    data_writer = Connector(interface='DataOutput')

    # Declare other class-level stuff

    # define __init__ and on_activate/on_deactivate

    # example method with calls to hardware module(s)
    def do_stuff(self):
        self.data_reader().start()  # Will call <MyHardwareModule>.start_read()
        self.data_writer().start()  # Will call <MyHardwareModule>.start_output()
```

As you can see through the use of the `Connector` object, the logic does not need to know if two 
separate devices are connected or a single device with overloaded interface methods.