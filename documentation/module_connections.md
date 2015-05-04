How to connect software modules                       {#moduleconnection}
============

Every module derived from Base has an OrderedDict "connector" which has to
contain its connection possibilities.

In the constructor __init__ of each derived class, this OrderedDict needs to be
updated to reflect if a connection interface is provided.

The connection interface is implemented as an Interface class that is inherited
by the class wishing to provide an interface.

The interface class constructor should check for the "connector" OrderedDict
and add the appropriate entries representing it.

The format of the "connector" OrderedDict is:

~~~~~~~~~~~~~
connector = OrderedDict
    in:
        uniqueName1:
            class: InterfaceClass1
            object: None
        uniqueName2:
            class: InterfaceClass2
            object: None
    out:
        uniqueNameX:
            class: InterfaceClassX
~~~~~~~~~~~~~

The Base class supplies the "connector" dict and its top level keys
"in" and "out".

Interface class constructors add everything below that.
Controlling something means adding an Interface under "in"
in the "connector^" dict.

In the configuration file, add the following structure to your module
to get your things connected

~~~~~~~~~~~~~
logic:
    stuff:
        module: 'odmrlogic'
        connect:
            mw1: 'mykrowave.1'
            mw2: 'mykrowave.2'
~~~~~~~~~~~~~

This will add a reference to the module loaded as "mykrowave" into
the "connector" dict of the "odmrlogic" module loaded as "stuff" at
~~~~~~~~~~~~~
    in:
        mw1:
            object: referenceToMycrowave
~~~~~~~~~~~~~
if the classes set in "class:" match  such that the "mykrowave" object has 
declared this class in an entry
~~~~~~~~~~~~~
    out:
        1:
            class:  MicrowaveInterface
~~~~~~~~~~~~~
and actually inherits the class MicrowaveInterface.


