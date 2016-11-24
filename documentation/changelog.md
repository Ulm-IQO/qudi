# Changelog {#changelog}

## Relese 0.6

## Release 0.5

Released on 30 Dec 2015.
Available at https://qosvn.physik.uni-ulm.de/svn/qudi/tags/release-0.5

Notes about this release are probably missing due to holidays.

 * Two photon counters supported in NI card counter and counter logic

## Release 0.4

Released on 30.10.2015.
Available at https://qosvn.physik.uni-ulm.de/svn/qudi/tags/release-0.4

New features:

 * Tilted scanning
 * ODMR remembers settings
 * ODMR can save raw data
 * Working and tested support for Radiant Dyes flip mirrors
 * support for taking spectra from spectrometer via WinSpec32
 * POI positions are now actually updated when the tracked POI moves
 * remote module support is more robust now
 * fixed a crash when changing confocal color bar while scanning
 * winspec32 spectrometer support
 * configurable settling time at start of optimization scans
 * option for surface-subtraction in the depth optimization scan
 * ALPHA Task interface
 * PRE-ALPHA for pulsed experiments

## Release 0.3

Released on 31.07.2015. Available at https://qosvn.physik.uni-ulm.de/svn/qudi/tags/release-0.3

New features:

 * Manager now includes log and iPython console
 * Manager can load and save the configuration
 * Manager can show active threads and remotely shared modules
 * QuDi remembers which configuration file is loaded
 * QuDi can restart to load new configuration
 * SmiQ R&S 06ATE works for ODMR
 * Dockwidgets in ODMR
 * Laser scanning with a remote wavemeter is now tested and confirmed working
 * Zoom with mouse in Confocal

Additionally, lots of bugs were fixed.

## Release 0.2

Release-0.2 is available since 07.07.2015.
It can be found using: https://qosvn.physik.uni-ulm.de/svn/qudi/tags/release-0.2

New features:

 * New Log style
 * (Manager shows module state)
 * Continues scan xy/depth (loop scan)
 * Rotate confocal images (rotates only the image, not the cursor!!!)
 * POI Manager GUI: restore default widget location (size might not be as default)
 * Cursor and arrow keys: right/left(x-direction) up/down(y-direction) Bild up/Bild down(z-direction); big step size with shift;step size can be changes in the settings
 * Clock time sample shift POI Manager
 * Centiles of colorbars is now working during a scan
 * All save files should now have the same time in the lable
 * duration of periodic optimiser changeable working during period
 * improved explanation in the data file of the Confocal scans
 * Added tooltips to Confocal and Optimiser settings

## Release 0.1

Release-0.1 is the first release of the QuDi software project.
It can be found via SVN Checkout using this URL: https://qosvn.physik.uni-ulm.de/svn/qudi/tags/release-0.1
It is possible to do basic measurements and the following modules are working:

 * Counter
 * Confocal scanning
 * Laser scanning
 * POI managing
 * ODMR

The basics of all these modules are working but there is plenty room for improvement.
At this stage the GUI is still under active development and so users should expect some interface items to change in future releases.

