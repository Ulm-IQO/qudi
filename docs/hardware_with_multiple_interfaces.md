# Creating hardware modules satisfying multiple interfaces {#multiple_interface_hardware}

This article will describe the qudi feature to overload interface attributes within hardware modules 
in case of namespace collisions between multiple inherited interface classes.

## Why do we even need this feature?
Imagine you have an interface class `DataReaderInterface` which interfaces a simple data reader device.
You also have another interface class `DataOutputInterface` which interfaces a simple data output device.
Now let's say you have a piece of hardware that can handle both tasks simultaneously and you want 
to write a hardware module for that.

First of all you would need to inherit both interfaces in the class definition of your hardware 
module:
```python
from qudi.interface.data_reader import DataReaderInterface
from qudi.interface.data_output import DataOutputInterface

class MyHardwareModule(DataReaderInterface, DataOutputInterface):
    """ This will become my new fancy hardware module to combine DataReaderInterface and 
    DataOutputInterface functionality
    """
    pass
```

So far so good...
Now let's have a closer look at the class members of `DataReaderInterface` and 
`DataOutputInterface`:
```python
from abc import abstractmethod
from qudi.core.module import Base


class DataReaderInterface(Base):
    """ This is a fictional data reader interface.
    """
    
    @property
    @abstractmethod
    def constraints(self):
        """ A read-only data structure containing all hardware parameter limitations. 
        """
        raise NotImplementedError

    @abstractmethod
    def get_data(self):
        """ Get the read data array.

        @return iterable: Data array
        """
        raise NotImplementedError

    @abstractmethod
    def start(self):
        """ Start the data acquisition.
        """
        raise NotImplementedError


class DataOutputInterface(Base):
    """ This is a fictional data output interface.
    """
    
    @property
    @abstractmethod
    def constraints(self):
        """ A read-only data structure containing all hardware parameter limitations. 
        """
        raise NotImplementedError

    @abstractmethod
    def set_data(self, data):
        """ Set the data array to output.

        @param iterable data: The data array to output
        """
        raise NotImplementedError

    @abstractmethod
    def start(self):
        """ Start the data output.
        """
        raise NotImplementedError
```

As you can see it will be no problem to just implement the `get_data` and `set_data` methods in our 
new hardware module since they have unique names that are just present in a single interface, 
respectively.
The method `start` and the property `constraints` however are an entirely different story. In a 
traditional way you can only define one attribute with that name in your hardware module, thus 
preventing to start each task separately and getting the constraints selectively.

And this is where the ominous meta object `qudi.util.overload.OverloadedAttribute` comes into play.

## How to overload an interface attribute
The meta object `OverloadedAttribute` enables you to flag any attribute 
(descriptor object, variable, method/function etc.) as an overloaded attribute giving the 
possibility to register multiple implementations for the attribute under unique `str` keys.

Let's look at an example on how this can be used in a hardware module based on the example classes 
presented in the previous section:
```python
from qudi.interface.data_reader import DataReaderInterface
from qudi.interface.data_output import DataOutputInterface
from qudi.util.overload import OverloadedAttribute

class MyHardwareModule(DataReaderInterface, DataOutputInterface):
    """ This will become my new fancy hardware module to combine DataReaderInterface and 
    DataOutputInterface functionality.
    """
    
    # Define qudi module activation/deactivation
    ...
    
    # Do other stuff
    ...
    
    def get_data(self):
        # Do something
        return tuple(range(42))

    def set_data(self, data):
        # Do something
        pass
    
    # Flag "start" attribute as overloaded attribute
    start = OverloadedAttribute()

    # Register multiple implementations for "start" via convenient decorator
    # The key words under which the implementations are registered must be the corresponding 
    # interface class names.
    # Make sure to use "start" as attribute name for all implementations.
    @start.overload('DataReaderInterface')
    def start(self):
        # Start the data reader
        print('Data reader started through "DataReaderInterface" interface method')
    
    @start.overload('DataOutputInterface')
    def start(self):
        # Start the data output
        print('Data output started through "DataOutputInterface" interface method')

    # You can do the same for properties. Just make sure to apply the @property decorator first.
    constraints = OverloadedAttribute()
    
    @constraints.overload('DataReaderInterface')
    @property
    def constraints(self):
        # Return data reader constraints
        print('Data reader constraints requested through "DataReaderInterface" interface.')
        return dict()

    @constraints.overload('DataOutputInterface')
    @property
    def constraints(self):
        # Return data output constraints
        print('Data output constraints requested through "DataOutputInterface" interface.')
        return dict()
```

As already mentioned, `set_data` and `get_data` do not need special treatment.

Through the `OverloadedAttribute` object and decorators used here, the two implementations for 
`start` will both be registered to the attribute `start`; each one associated to a different 
interface class name ('DataReaderInterface' or 'DataOutputInterface').
Same goes for the property `constraints`.

The string given in the `overload` decorator is used as a keyword to address which implementation 
to use:
```python
# Call different implementations for "start"
<MyHardwareModule>.start['DataReaderInterface']()
<MyHardwareModule>.start['DataOutputInterface']()
# Get different implementations for "constraints" property
<MyHardwareModule>.constraints['DataReaderInterface']
<MyHardwareModule>.constraints['DataOutputInterface']
```

So when accessing overloaded attributes of a hardware class directly, you can select which 
implementation to address by adding the respective overload keyword in square brackets after the 
method name just as you would for any mapping in Python.

Using keywords that have not been registered will result in `KeyError`.

You can however always overwrite the interface attribute in your hardware class as usual by just 
defining it regularly (without the decorator and the meta object) if you do not need to overload it.

## Interface methods and logic module Connector
Now you might think this new way of addressing overloaded attributes will not work seamlessly with 
logic modules due to the changed attribute access syntax.

In order to work around this issue the `qudi.core.connector.Connector` object is your best friend. 
During instantiation of a `Connector` object the logic module passes the interface type or class 
name as parameter. As such the `Connector` instance can provide a hardware module proxy object when 
called to hide the overload mechanics of interface methods from the calling logic module. 
This is enabled by `qudi.util.overload.OverloadProxy`.

To illustrate this further, let's assume you have a logic module `MyLogicModule` which is 
interfacing `DataReaderInterface` and `DataOutputInterface` through our new hardware module 
`MyHardwareModule`.
A call to each different `start` implementation would look like:
```python
from qudi.core.connector import Connector
from qudi.core.module import LogicBase

class MyLogicModule(LogicBase):
    """ Fictional logic module illustrating the use of the Connector object with overloaded 
    interface methods.
    """
    # Instantiate connectors    
    _data_reader = Connector(name='data_reader', interface='DataReaderInterface')
    _data_output = Connector(name='data_output', interface='DataOutputInterface')

    # Declare other class-level stuff
    ...

    # define qudi module on_activate/on_deactivate
    ...
        
    # example method with calls to hardware module(s)
    def do_stuff(self):
        self._data_reader().start()  # Will call "start" implementation for "DataReaderInterface"
        self._data_output().start()  # Will call "start" implementation for "DataOutputInterface"
```

As you can see through the use of the `Connector` object, the logic does not need to know if two 
separate devices are connected or a single device with overloaded interface methods.

## Generalization
The qudi meta object `OverloadedAttribute` as well as `OverloadProxy` can in fact be used in a very 
general way and not only with qudi hardware interfaces.

It can overload any attribute type (descriptor objects, callables, staticmethods, classmethods, 
etc.) in the class body with any non-empty `str` keywords. You do not need qudi module base/meta 
classes for the overload mechanism to work, which allows you to use it with any Python3 class.
The same is true for hiding the overloading semantics using `OverloadProxy`.
