# Interfuses {#how_to_interfuses}

## General Definition 

Building on the abstraction of interfaces, Qudi introduces an additional concept 
to reuse modules for different tasks. Such modules are called interfuse files 
(in contrast to interfaces). 

These files interconnect (or fuse) different hardware or logic modules to modify
interface behavior or to achieve a task that these modules were originally not 
designed for. The main task of an interfuse is to convert the calls of a logic 
module using an interface A to an interface B or to modify the behavior of an 
interface. By construction, interfuses are logic modules that happen to 
implement interfaces for hardware modules. Therefore interfuse files are 
situated in the folder

    ./logic/interfuse

Since the core logic operations remain in the specific logic module and are not 
re-implemented to satisfy new hardware interfaces and the initial hardware 
modules are not touched we retain modular structure and compatibility to old 
interfaces. This practice improves maintainability and prevents code 
duplication.


## Examples for Interfuses

In order to understand the concept and intension of interfuses and their 
implementation some examples are given in the following.

### Interfuse replaces a counter by a spectrometer in Confocal logic

A confocal image (2D array) can represent single fluorescence values from a 
photon counter for each tuple of position (x, y). Using an interfuse, we can 
replace the counter with a spectrometer and obtain a depiction of a selected 
fluorescence wavelength value depending on the position (x, y) in the scanner image. 
The interfuse for that example is the file
    
    confocal_scanner_spectrometer_interfuse.py

### Interfuse combines motorized stage with magnet logic

As a second example, a magnet logic controls the magnetic field e.g. by 
adjusting the current though different coils. A stepper motor with a permanent 
magnet attached can later replace the coils. The magnet motor interfuse serves 
as mediator converting the magnetic field change request by altering the 
position of the magnet in relation to the sample. Instead of rewriting the 
interface to the coils (which might be used elsewhere as well) to fit both 
methods and alter the magnet logic and GUI to use the new interface, an 
interfuse allows both to be addressed without any changes to logic and GUI.

In order to be addressed by the (magnet) logic the magnet_motor_interfuse should
inherit the (magnet) interface and reimplement (overload) each method from the 
magnet interface. Given the fact that it will convert a magnet logic call to a 
motor hardware call, the magnet_motor_interfuse file has to stick to the 
interfaces methods of the motor interface. The interfuse for that example is the
file.
    
    magnet_motor_interfuse.py

### Interfuse enables tilt correction by altering the interface calls

An interfuse can also be used as an additional layer between the already 
existing logic and hardware, e.g. calculating a tilt correction of a position 
scan and altering the way of scanning. As a result, an actually tilted surface 
appears flat again in the confocal image and can then be imaged at a consistent 
depth. The interfuse for that example is the file

    scanner_tilt_interfuse.py