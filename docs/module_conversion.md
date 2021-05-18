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
``` python
from qudi.core.module import Base, LogicBase, GuiBase
```
Notice, that the base class for the logic also has been renamed.

As the Interfaces now inherite from the base class, 
you do not need to inherit again from `Base` if you make your custom class 
confirm to an interface by inheriting it. 
Therefore the follwoing will suffice e.g. for a new hardware switch module:
``` python
from qudi.interface.switch_interface import SwitchInterface

class SwitchDummy(SwitchInterface):
    pass
```

Often used connectors are:
``` python
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.util.mutex import Mutex, RecursiveMutex
```
## Interfaces

## Saving and fitting

## threading

##  miscellaneous