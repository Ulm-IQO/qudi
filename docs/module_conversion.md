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

Common objects used in qudi modules are:
```Python
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import Mutex, RecursiveMutex  # use Mutex over RecursiveMutex whenever possible
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

## Threading
In general threading in qudi should not be handled directly but through Signals in QT. 
All the logic modules run in their own threads, as can be seen when selecting the 
thread view in the qudi main window. GUI modules have to run in the Qt main thread 
while hardware modules do not have their own threads by default and their functions are run 
by the calling thread (probably logic).
You can however also force a hardware module to run in its own thread by setting `_threaded = True` 
in the module class definition, e.g.:
```Python
class MyThreadedHardware(MyInterface):
    _threaded = True
    ...
```

If you do however need explicit threading, please use the qudi thread manager, 
so it keeps track of them and also shows them in the thread view.

A simple example for spawning a worker thread and executing a worker method inside this thread.
```Python
import time
from PySide2.QtCore import QObject, QThread
from qudi.core.threadmanager import ThreadManager


class Worker(QObject):
    """ This is a classical worker class that can run a script defined e.g. in "do_stuff"
    """
    def do_stuff(self):
        print(f'Worker started in thread: "{QThread.currentThread().objectName()}"')
        # work on stuff, e.g. something that takes 5 seconds to complete
        time.sleep(5)
        print(f'Worker finished in thread: "{QThread.currentThread().objectName()}"')
        
        
def run_in_thread(thread_name='MyThread'):
    """ This function will spawn and run a new worker thread and waits until it has finished.
    
    @param str thread_name: The custom name of the thread to spawn
    """
    # Check if thread manager can be retrieved from the qudi main application
    thread_manager = ThreadManager.instance()
    if thread_manager is None:
        raise RuntimeError('No thread manager found. Qudi application is probably not running.')
    # Get a newly spawned thread (PySide2.QtCore.QThread) from the thread manager and give it a name
    my_thread = thread_manager.get_new_thread(thread_name)
    # Create worker instance and move the worker object to the new thread
    my_worker = Worker()
    my_worker.moveToThread(my_thread)
    # Connect the QThread.started signal to the worker "run"-method.
    # This will cause the worker to execute its "do_stuff" method as soon as the corresponding
    # thread is up and running.
    my_thread.started.connect(my_worker.do_stuff)
    # Start the thread and let the worker run
    my_thread.start()
    # Issue stopping the thread. This will not wait until it has actually stopped.
    thread_manager.quit_thread(my_thread)
    # Wait until it has actually finished running and the thread is stopped.
    # The thread manager will clean up the created thread automatically after it has stopped so 
    # you can not re-run a thread after it has stopped
    thread_manager.join_thread(my_thread)
```

## Miscellaneous

- The former `qudi_slot` mechanism does not exist anymore. 
  Just use normal slots from Pyside.
- ui-files created with the QTDesigner can contain promoted widgets that directly 
  link to qudi custom widgets. In this case the path to the custom widgets needs to be replaced.
  e.g. `qtwidgets.scientific_spinbox.h` becomes `qudi.core.gui.qtwidgets.scientific_spinbox`
- On some Windows 10 system the following error might appear after installation of the new core:\
`ImportError: DLL load failed while importing win32api: The specified module could not be found.`\
  There is a bug report on that [here](https://github.com/jupyter/notebook/issues/4980). \
  An estabilished workaround is to call the following in you new qudi environment. 
  This is actually not a fix, but by upgrading the pywin32 package with pip 
  you make sure that the PATH is set correctly independent of the buggy conda: \
  `pip install –upgrade pywin32==225`
