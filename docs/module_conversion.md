# Module conversion from old qudi to new core {#module_conversion}
This document should give a short introduction on how to convert custom modules 
that have work with old qudi to work with the new qudi core. 
In principle the new core follows the same ideas as the old qudi, 
so the structure of any custom modules can stay the same with a few smaller changes. 

Here we want to list common points that sould be considered when converting modules.

## Imports
All the imports of the qudi core modules have changed from e.g. 
`from core.connector import Connector` to now have a `qudi.` infront of it. 
So the new import of the connector would be: `from qudi.core.connector import Connector`

Also the base modules of your custom qudi classes have changed to:
```Python
from qudi.core.module import Base, LogicBase, GuiBase
```
Notice, that the base class for the logic also has been renamed.

As the Interfaces now inherite from the base class, 
you do not need to inherit again from `Base` if you make your custom class 
confirm to an interface by inheriting it. 
Therefore the follwoing will suffice e.g. for a new hardware switch module:
```Python
from qudi.interface.switch_interface import SwitchInterface

class SwitchDummy(SwitchInterface):
    pass
```

Often used connectors are:
```Python
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import Mutex, RecursiveMutex
```
## Interfaces
The old way of declaring an intraface was:
```Python
from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass

class DummyInterface(metaclass=InterfaceMetaclass):
    @property
    @abstract_interface_method
    def name(self):
        """ The name of the Module.
        @return str: name
        """
        pass
```

The new way of declaring an interface is as follows:
```Python
from abc import abstractmethod
from qudi.core.module import Base

class DummyInterface(Base):
    @property
    @abstractmethod
    def name(self):
        """ The name of the Module.
        @return str: name
        """
        pass
```
Notice that the interface is now inheriting the Base class and that the pure `abcabstractmethod` is used.

## Saving and fitting

Fitting and saving is now part of the core itself and does not belong to a logic module. 
Therefore both can be accessed via core-imports instead of with connectors.

For details please see [Saving](data_storage.md) and [Fitting](data_fitting_integration.md).

## threading
In general threading in qudi should not be handled directly but through Signals in QT. 
All the logic modules run in their own threads, as can be seen when selecting the 
thread view in the qudi manager. GUI modules have to run in the QT-main-thread 
while hardware modules do not have their own threads and their functions are run 
by the calling thread (probably logic).

If you do however need explicit threading, please use the qudi thread manager, 
so it keeps track of them and also shows them in the thread view.

A simple example is given below:
```Python
import threading
from qudi.core.threadmanager import ThreadManager

class Dummy:
    def start(self):
        print(f'I am running in thread: {threading.current_thread().name}')

def run_in_thread():
    thread_name = 'MyThread'
    thread_manager = ThreadManager.instance()
    if thread_manager is None:
        return False
    thread = thread_manager.get_new_thread(thread_name)
    runner = Dummy()
    self._instance.moveToThread(thread)
    thread.start()
    QtCore.QMetaObject.invokeMethod(runner,
                                    'start',
                                    QtCore.Qt.BlockingQueuedConnection)

```

##  miscellaneous

- The former `qudi_slot` mechanism does not exist anymore. 
  Just use normal slots from Pyside.
- ui-files created with the QTDesigner can contain promoted widgets that directly 
  link to qudi custom widgets. In this case the path to the custom widgets needs to be replaced.
  e.g. `qtwidgets.scientific_spinbox.h` becomes `qudi.core.gui.qtwidgets.scientific_spinbox`
