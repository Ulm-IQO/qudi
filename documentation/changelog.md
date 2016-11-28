# Changelog {#changelog}

## Relese 0.6

Released on 25 Nov 2016.
Available at https://github.com/Ulm-IQO/qudi/releases/tag/v0.6 .

Changes/New features:

 * Lots and lots of work leading to working and stable pulsed measurement modules, including
   * Editor for fast analog and digital waveforms and AWG channel configuration
   * Synthesize and upload waveforms to AWGs while respecting AWG limits and channels
   * Pulse extraction from fast counter time trace and flourescence signal extraction
   * Display of results for common measurements
   * Works with Jupyter notebooks
 * Some new documentation
 * Preliminary GUI to show/edit configuration files
 * Massive improvements to fit stability
 * Most interfaces now use abstract base classes
 * Confocal can show last scanned line and move Z while scanning XY
 * Continuous integration support
 * Nuclear spin operations experiment module
 * Spinboxes with scientific notation support
 * Use QtPy to support multiple Qt versions
 * Configuration files now use the YAML file format
 * Cooperative inheritance for modules
 * Logging now based on standard Python logger
 * HighFinesse WSU 30 wave meter support
 * New and consistent colors for plots throughout Qudi
 * PyQt5 compatibility
 * Many fixes to QO and Pi3 FPGA fast counter modules
 * Matplotlib inline plots and completion suport for Jupyter kernel
 * Jupyter kernel for Qudi (including install script)
 * Move project repository from SVN to git and to GitHub
 * New dark color scheme for GUI (modified qdark)
 * Lots of new predefined fitting methods
 * Fit logic can now load fitting methods from python files in a subfolder
 * Reusable fit settings GUI methods
 * Tektronix AWG 70000, 7112 and 5002 support
 * Gated counter logic and GUI modules
 * Magnetic field alignment module for vector magnet and solid state magnet on a 4-axis stage
 * Thorlabs APTmotor support
 * Scan history (Forward/backward) in Confocal
 * Qudi module state save/restore functionality (app_status folder)
 * Automatic loading of configured modules on a remote system
 * UI fixes
 * TSYS_01 temperature sensor support
 * Raspberry Pi PWM support for PID
 * Software PID logic and GUI
 * Fastcomtec 7887 and MCS6 support
 * Picoharp300 support
 * Python script to list qudi modules

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

