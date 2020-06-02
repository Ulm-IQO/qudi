# Changelog {#changelog}

## Pre-release

Changes/New features:

* Cleanup/Improvement/Debug of POI manager (logic and GUI)
* New POI manager tool _POI selector_ which allows adding of new POIs by clicking inside the scan 
image
* Added an optional POI nametag to the POI manager. If you give this property a string value, all 
new POIs will be named after this tag together with a consecutive integer index.
* If using the POI manager, the currently selected active POI name will be added to savelogic as 
global parameter. All saved data files will include this POI name in the header.
* bug fix to how the flags are set for AWG70k
* New POI automatic search tool added. If you click on the 'Auto POIs' tool button, POIs will be 
automatically added in your scan image. This makes fluorescent emitter selections much faster and
more accurately.
* Replaced the old `pg.PlotWidget` subclass `PlotWidgetModified` with new subclasses 
`ScanPlotWidget`, `ScanViewBox` (`pg.ViewBox`) and `ScanImageItem` (`pg.ImageItem`) to handle 
coordinate transformations upon mouse click/drag and zooming internally. Also integrates the 
draggable crosshair into the PlotWidget. This reduces code and improves readability in GUI modules.
* Introduced blink correction filter to confocal and poimanager scan images (toggle in "view" menu). 
Purely for displaying purposes; raw data is not affected by this filter.
* Add `scan_blink_correction` filter to `core.utils.filters`
* exposed the sequencegenerator-functions analyze_sequence and analyze_ensemble to be accessible via pulsedmaster
* analyze functions can be called either with the appropriate objects or with the object name
* while sampling a sequence, the ensembles are only sampled if they weren't already sampled before
* Add `natural_sort` utility function to `core.util.helpers`
* Bug fix to the gated extractor: now all the function parameters are loaded
* Added a hardware file for power supply Keysight E3631A with a process control interface
* Updated powermeter PM100D module to add ProcessInterface and wavelength support
* Added two interfuses for interfaces process value and process control to modify the values based
on an interpolated function
* Changed ProcessInterface and ProcessControlInterface to use underscore case instead of CamelCase
* Added hardware module to interface temperature controller Cryocon 22C
* Added an optional parameter to connectors so that dependencies can be optional
* Made ODMR logic an optional dependency in SpectrumLogic
* Made some changes in the AWG7k file for sorting integers without natural sort
* Removed additional scaling from sampling functions. They now return samples as as expected. 
The entire normalization to pulse generator analog voltage range (Vpp) is done during sampling.
* Introduced support of interface sensitive overloading of interface methods. This resolves 
namespace conflicts within a hardware module inheriting multiple interfaces. See 
_how_to_hardware_with_multiple_interfaces.md_ for detailed documentation.
* Used the new (already existing) helper function _add_trigger in the shipped `predefined_methods`.
* Added more extraction and analysis methods for extraction and/or analysis that is done directly on hardware.
* Improved the jupyter kernel: prints are now printed live and not only after the cell is finished. Also code cleanup.
* Add two different chirp functions to sampling functions and predefined methods
* Adding Ocean optics spectrometer hardware module.
* Removed the method `has_sequence_mode` from the `PulserInterface` 
and rather added a `sequence_option` to the `PulserConstraints`.
In `FORCED` mode the `SequenceGeneratorLogic` will create a default sequence around each stand-alone Ensemble.
The potential sequence_options are: 
  * `NON` (no sequence mode)
  * `OPTIONAL` (sequence mode possible)
  * `FORCED` (only output as sequence possible)
* Added interfuse to correct geometrical aberration on scanner via polynomial transformations
* added the option to do a purely analog ODMR scan.
* added multi channel option to process_interface and process_control_interface
* added the option of an additional path for fit methods
* added a hardware file for power supply  Teledyne T3PS3000
* added pulse generator constraints to predefined
* remove debug prints for flags in dummy pulser that were filling up the log
* wider first column for ensemble and sequence editors to see long names and fixing header of first column in table of sequence editor
* Added config option for counter voltage range in hardware class NationalInstrumentsXSeries.
* Saving data in confocal GUI no longer freezes other GUI modules
* Added save_pdf and save_png config options for save_logic
* Fixed bug in spincore pulseblaster hardware that affected only old models
* Added a netobtain in spincore pulseblaster hardware to speedup remote loading 
* Adding hardware file of HydraHarp 400 from Pico Quant, basing on the 3.0.0.2 version of function library and user manual.
* reworked the QDPlotter to now contain fits and a scalable number of plots. Attention: custom notebooks might break by this change.
* Set proper minimum wavelength value in constraints of Tektronix AWG7k series HW module
* Fixed bug affecting interface overloading of Qudi modules


Config changes:

* The parameters `additional_predefined_methods_path` and `additional_sampling_functions_path` 
of the `SequenceGeneratorLogic` can now either be a string for a single path 
or a list of strings for multiple paths.
* There is an option for the fit logic, to give an additional path: `additional_fit_methods_path`
* The connectors and file names of the GUI and logic modules of the QDPlotter have been changed.
* QDPlotter now needs a new connection to the fit logic. 

## Release 0.10
Released on 14 Mar 2019
Available at https://github.com/Ulm-IQO/qudi/releases/tag/v0.10

Changes/New features:

* Added support for Opal Kelly XEM6310-LX45 devices to HardwareSwitchFpga hardware module.
* Newport CONEX-AGP piezo stage motor module.
* Sequence Generator checks the step constraint and adds and idle block if necessary.
* Save_logic now expands environment variables in the configured data path (e.g. $HOME under Unix or $HOMEPATH under Windows)
* Added command line argument --logdir to specify the path to the logging directory
* Added the keyword "labels" to the "measurement_information" dict container in predefined methods.
This can be used to specify the axis labels for the measurement (excluding units)
* All modules use new connector style where feasible.
* Bug fix for POI manager was losing active POI when moving crosshair in confocal
* Added a how-to-get-started guide to the documentation
* Bug fixes and improvements for the scientific SpinBox introduced in v0.9 
* POI manager keeps POIs as StatusVar across restarts and fixes to distance measurement
* Various stability improvements and minor bug fixes
* Update conda environment to more recent versions of packages
* Fix installation procedure for the conda environment in windows by using powershell in the cmd and catch with that potential exceptions (e.g. if conda environment is not present).
* Added .ico image to make a desktop shortcut on Windows with explanation in the documentation
* Added a how-to-participate guide to the documentation
* Added installation options guide to the documentation
* A lot of smaller fixes to the spectrometer (WinSpec) -> this also modifies the connectors in the default config
* Added fitting to the spectrometer
* Microwave interface passes trigger timing to microwave source, needs hardware module adjustments for not-in-tree modules
* Bug fixes and support for SMD12 laser controller
* For SMIQs added config options to additionally limit frequency and power. Added constraint for SMQ06B model.
* Added live OMDR functionality to only calculate the average signal over a limited amount of scanned lines
* New hardware file for Microwave source - Anritsu MG3691C with SCPI commands has been added.
* **Config Change:** Hardware file for mw_source_anritsu70GHz.py with class MicrowaveAnritsu70GHz was changed to file mw_source_anritsu_MG369x.py with class MicrowaveAnritsuMG369x to make it universal. Also hardware constraints are set per model.
* Lock-In functionality was added to the ODMR counter and implemented for the NI-Card. All other hardware and interfuse with ODMRCounterInterface were updated.
* New hardware file for Microwave source - WindFreak Technologies SynthHDPro 54MHz-13GHz source
* New hardware file for AWG - Keysight M3202A 1GS/s 4-channel PXIe AWG
* Add separate conda environments for windows 7 32bit, windows 7 64bit, and windows 10 64bit. 
* Extend the windows installation procedure of the conda environment for qudi. The conda environments is selected automatically for the correct windows version and the appropriate environment file is taken.
* Rewrite the documentation for required python packages for Qudi and mention instead the installation procedure, how to create manually a python environment for qudi.
* Correct the low level implementation for the PulseBlasterESR-PRO.
* Implement the pulser interface for PulseBlasterESR-PRO devices.
* Implement the switch interface for PulseBlasterESR-PRO devices.
* Add possibility to set instruction delays in the config for PulseBlasterESR-PRO sequence generation.
* Add a copy-paste config option to the docstrings of all current qudi hardware modules.
* Add save logic features to add additional parameters saved with each data file
* **Pulsed 3.0:**\
    _A truckload of changes regarding all pulsed measurement related modules_
    * analyze_sequence now returns all the necessary values to work with sequences.
    * It is now possible to select no or analogue laser channels. In this case, the relevant block element gets marked as laser.
    * Adding the possibility to reliably add flags to sequence steps and making them selectable in the GUI.
    * Bug fix for waveform generation larger than ~2 GSamples
    * Added chirp function to available analog shapes in pulsed measurements
    * Tab order in pulsed measurement GUI is now more useful
    * Added delta plot of alternating sequence in the pulsed analysis window (including errorbars)
    * Bug fix for pulsed extraction window where zooming caused InfiteLines to disappear and a 
    switch in lines caused negative width
    * Bug fix for pulsed measurements with large photon count numbers (`numpy.int32` vs. 
    `numpy.int64`)
    * Pulsed related logic modules have been moved to `<main_dir>/logic/pulsed`
    * Graphical editors for `PulseBlock`, `PulseBlockEnsemble` and `PulseSequence` instance 
    generation are now implemented according to the _Qt_ model/view concept. Several delegates and 
    custom widgets needed by the editors can be found in `<main_dir>/gui/pulsed`. The editors 
    (_QTableView_) and corresponding models (_QAbstractTableModel_) can be found in 
    `pulse_editors.py`.
    * Several GUI tweaks and clean-ups for all tabs of `PulsedMeasurementGui`
    * Removal of several "logic components" from GUI module
    * `SequenceGeneratorLogic` is now fully responsible for controlling the pulse generator hardware.
    `PulsedMeasurementLogic` also has access to the pulse generator but only to start/stop it.
    `samples_write_methods.py` became obsolete and will be removed once all hardware modules 
    implement waveform/sequence generation on their own.
    * The purpose of `PulsedMasterLogic` is now mainly to decouple function calls to 
    `SequenceGeneratorLogic` and `PulsedMeasurementLogic` via signals. Due to the very diverse 
    usage of the pulsed modules in a combination of custom scripts together with the GUI this is 
    a crucial feature to ensure safe threading.
    * Pulser hardware interface has been changed. The pulser hardware module is now fully 
    responsible for waveform and sequence generation on the device. The `SequenceGeneratorLogic` 
    now only calculates the analog and digital samples and hands them over to the hardware module 
    to be written to the device. This makes it more flexible since no in-depth knowledge about the 
    hardware specific memory/file management is needed in the logic making the interface more 
    generic. Makes it easier to create new pulse generator modules as long as the hardware can be 
    abstracted to a waveform/sequence terminology.
    * Adapted pulse generator modules to new pulser interface.
    * Adapted FPGA hardware file to run with new interface.
    * All groups of settings in pulsed logic modules are now represented as dictionaries improving 
    flexibility as well as minimizing necessary code changes when adding new features.
    * Most parameter sets in `PulsedMeasurementLogic` and `SequenceGeneratorLogic` are now 
    properties of the respective module. `PulsedMasterLogic` also provides an interface to all those 
    properties.
    * Dynamic import of pulse analysis and pulse extraction methods now realized through helper 
    class instances held by `PulsedMeasurementLogic`. For detailed information about adding 
    methods, please see `how_to_add_analysis_methods.md` and `how_to_add_extraction_methods.md`
    * Dynamic import of predefined methods now realized through helper class instance held by 
    `SequenceGeneratorLogic`. For detailed information about adding methods, please see 
    `how_to_add_predefined_methods.md`
    * Dynamic import of sampling function definitions (analog waveform shapes) handled by class 
    `SamplingFunctions` and will be refreshed upon activation of `SequenceGeneratorLogic`. For 
    detailed information about adding functions, please see `how_to_add_sampling_functions.md`
    * Alternative plot data will now always be saved if available
    * Automatic setting of parameters in pulsed analysis tab (invoke settings) will only be possible
    for ensembles/sequences generated by predefined methods (instances must have fully populated 
    `measurement_information` dictionary) NOT for ensembles/sequences created or edited by the table
    editors.
    * Each `PulseBlockEnsemble` and `PulseSequence` instance will have a dictionary attribute called
    `sampling_information` which will be populated during waveform/sequence creation. It provides 
    information about the "real life" realization of the waveform/sequence like the actual length of
    each `PulseBlockElement` in integer time bins or the times at which transitions of digital 
    channels occur. It will also contain the set of pulse genrator settings used during sampling 
    (e.g. sample_rate, activation_config etc.).
    When the respective pulser assets (waveforms and sequences) get deleted from the device, this 
    dictionary will be emptied to indicate that the asset has not yet been sampled.
    This will only work if you delete waveforms/sequences on the device via qudi commands or upon a 
    restart of qudi. Hardware assets directly deleted by hand can lead to faulty behaviour of the 
    pulsed measurement modules.
    * Pulse analysis and extraction methods now have read-only access to the entire 
    `PulsedMeasurementLogic` allowing to implement more sophisticated methods that need in-depth 
    information about the running waveform.
    * Predefined methods now have read-only access to the entire `SequenceGeneratorLogic`
    * Pulsed object instances (blocks, ensembles, sequences) are serialized to a directory that can 
    be changed via ConfigOption. Each instance is a separate file so it is easier to manage a large 
    number of instances. In the future these instances need to be saved as StatusVars
    * New dialog box for pulse generator hardware settings. Previously the settings were located 
    directly in a tab of the PulsedMainGUI. Also added voltage settings for digital and analog 
    channels that were missing in the GUI before. 
    * Lots of smaller changes to improve programming flexibility and robustness against users
	* Added a new ungated extraction method ('ungated_gated_conv_deriv') which uses the keys in the 
	  sampling information to convert an ungated timetrace into a gated timetrace which is then 
	  anaylzed with the ungated method 'gated_conv_deriv'. The conversion is based on the rising
	  and falling bins in the laser channel which indicate the positions of the laser pulses in 
	  the ungated trace. For fine-tuning additional delays (for example from AOMs) can be taken 
	  into account. This method speeds up laser extractions from ungated timetraced by a lot.
	* Improved pulsed measurement textfile and plot layout for saved data
    * Added buttons to delete all saved PulseBlock/PulseBlockEnsemble/PulseSequence objects at once.
    * Introduced separate fit tools for each of the two plots in the pulsed analysis tab
    * Automatically clears fit data when changing the alternative plot type or starting a new 
      measurement.

Config changes:
* **All** pulsed related logic module paths need to be changed because they have been moved in the logic
subfolder "pulsed". As an example instead of
    ```
    module.Class: 'pulsed_master_logic.PulsedMasterLogic'
    ```
    it should be now
    ```
    module.Class: 'pulsed.pulsed_master_logic.PulsedMasterLogic'
    ```
* `PulseExtractionLogic` and `PulseAnalysisLogic` are no qudi logic modules anymore and must be 
removed from the config. Also remember to remove them from the "connect" section of all other 
modules (probably just `PulsedMeasurementLogic`).

* The connection to `SaveLogic` has been removed from `PulsedMeasurementGui` and thus needs to be 
removed from the "connect" section in the config. So the GUI entry in the config should look 
somewhat like:
    ```
    pulsedmeasurement:
        module.Class: 'pulsed.pulsed_maingui.PulsedMeasurementGui'
        connect:
            pulsedmasterlogic: 'pulsedmasterlogic'
    ```
    
* The connectors and ConfigOptions for `SequenceGeneratorLogic` have changed. The new config should 
look somewhat like:
    ```
    sequencegeneratorlogic:
        module.Class: 'pulsed.sequence_generator_logic.SequenceGeneratorLogic'
        assets_storage_path: 'C:/Users/username/saved_pulsed_assets'  # optional
        additional_predefined_methods_path: 'C:\\Custom_dir'  # optional
        additional_sampling_functions_path: 'C:\\Custom_dir'  # optional
        connect:
            pulsegenerator: 'mydummypulser'
    ```
    Essentially "additional_predefined_methods_path" and "additional_sampling_functions_path" only 
    need to be specified when you want to import sampling functions or predefined methods from an 
    additional directory other than the default directories situated in qudi.logic.pulsed.
    "assets_storage_path" is the directory where the object instances for blocks, ensembles and 
    sequences are saved to. If not specified this directory will default to a subfolder in the home 
    directory.

* The connectors and ConfigOptions for `PulsedMeasurementLogic` have changed. The new config should 
look somewhat like:
    ```
    pulsedmeasurementlogic:
        module.Class: 'pulsed.pulsed_measurement_logic.PulsedMeasurementLogic'
        raw_data_save_type: 'text'  # optional
        additional_extraction_path: 'C:\\Custom_dir'  # optional
        additional_analysis_path: 'C:\\Custom_dir'  # optional
        connect:
            fastcounter: 'mydummyfastcounter'
            pulsegenerator: 'mydummypulser'
            fitlogic: 'fitlogic'
            savelogic: 'savelogic'
            microwave: 'microwave_dummy'
    ```
    Essentially "additional_extraction_path" and "additional_analysis_path" only need to be 
    specified when you want to import sampling functions or predefined methods from an additional 
    directory other than the default directories situated in qudi.logic.pulsed.
* The fitting has been added to the spectrometer logic module. You need to connect the FitLogic to 
the SpectrometerLogic module like:
    ```
    spectrumlogic: 
    module.Class: 'spectrum.SpectrumLogic' 
    connect: 
        spectrometer: 'myspectrometer' 
        savelogic: 'savelogic' 
        odmrlogic: 'odmrlogic' 
        fitlogic: 'fitlogic'
    ```

* Tektronix 7000 series is now in file `tektronix_awg7k.py` and class `AWG7k`.
 Use that instead of `tektronix_awg7122c.py` and change the configuration like this:
    ```
    pulser_awg7000:
        module.Class: 'awg.tektronix_awg7k.AWG7k'
        awg_visa_address: 'TCPIP::10.42.0.211::INSTR'
        awg_ip_address: '10.42.0.211'
        timeout: 60

   ```
   
## Release 0.9
Released on 6 Mar 2018
Available at https://github.com/Ulm-IQO/qudi/releases/tag/v0.9

Changes/New features:

* Huge amount of small and medium sized bug fixes and usability/stability improvements
* Replaced scientific SpinBoxes with a new implementation that is more powerful and does not use pyqtgraph
* Fixed Python crash upon closing qudi which was related to saving images with matplotlib (Windows)
* Added hardware module to control _Coherent OBIS_ lasers
* Manager GUI now properly reflects the state of each module
* Full multichannel support for slow counting / confocal / ODMR
* Moved to fysom v2.1.4
* Module base classes now nest fysom state machine in `module_state` instead of subclassing it. The current state is accessible via `module_state.current` or `module_state()`
* Changed the sampling algorithm for waveforms. Formerly each `PulseBlockElement` was sampled to match the specified length as closely as possible. Now the ideal time on which a transition between elements should occur is matched to a global quantized timeline. The sampled waveform length will now not deviate more than one timebin from the ideal length. However ideally identical elements can slightly vary (1 bin) in length throughout the entire waveform. This should lead in general to better results since the overall definition of the waveform is more closely matched to a quantized timeline
* Commonly used parameters in pulsed measurements are now shared for all predefined methods (less input widgets / clean UI). Each `generate_*` method still needs all parameters but input widgets are reused by name. Available names are:
  ```
  ['mw_channel', 
   'gate_count_channel', 
   'sync_trig_channel', 
   'mw_amp', 
   'mw_freq', 
   'channel_amp', 
   'delay_length', 
   'wait_time', 
   'laser_length', 
   'rabi_period']
  ```
* Generalized APT motor stages class (multi-axis support via config)
* Simple digital channel based switch on/off capability added to `hardware/ni_card.py`
* _National Instruments X series_ card hardware module renamed from `ni_card.py` to `national_instruments_x_series.py`
* `qudikernel.py` moved to core
* Listening address and port of qudi can now be changed in config (default: localhost)
* Analog signal input (for PDMR measurements) now supported for slow counter/confocal/ODMR (see config changes)
* Use of rpyc became optional (does not need to be installed if no remote module capability is needed)
* Mayor cleanup/overhaul of the `microwave_interface.py` and adaption of all affected modules (hardware/logic)



Config changes:
 * New remote server declaration (old one working but deprecated):
  ```
  [global]
  module_server:
      address: ''
      port: 12345
      certfile: 'filename.cert'
      keyfile: 'filename.key'
  ```

 * New full example config for `national_instruments_x_series.py`:
 ```
 mynicard:
     module.Class: 'national_instruments_x_series.NationalInstrumentsXSeries'
     clock_channel: '/Dev1/Ctr0'
     scanner_clock_channel: '/Dev1/Ctr2'
     photon_sources:
         - '/Dev1/PFI8'
         - '/Dev1/PFI9'
     counter_channels:
         - '/Dev1/Ctr1'
     counter_ai_channels:  # optional
         - '/Dev1/AI1'
     scanner_counter_channels:
         - '/Dev1/Ctr3'
     scanner_ai_channels:  # optional
         - '/Dev1/AI0'
     scanner_ao_channels:
         - '/Dev1/AO0'
         - '/Dev1/AO1'
         - '/Dev1/AO2'
         - '/Dev1/AO3'
     scanner_position_ranges:
         - [0e-6, 200e-6]
         - [0e-6, 200e-6]
         - [-100e-6, 100e-6]
         - [-10, 10]
     scanner_voltage_ranges:
         - [-10, 10]
         - [-10, 10]
         - [-10, 10]
         - [-10, 10]
     default_samples_number: 10
     default_clock_frequency: 100
     default_scanner_clock_frequency: 100
     gate_in_channel: '/Dev1/PFI9'
     counting_edge_rising: True
     odmr_trigger_channel: '/Dev1/PFI15'
 ```

## Release 0.8

Released on 2 Mar 2017.
Available at https://github.com/Ulm-IQO/qudi/releases/tag/v0.8

Caution: fits need to be configured in the respective settings dialog and
may not include printed results or may be just broken.
If you find a defective fit, consider fixing it and submitting a pull request.

Changes/New features:

 * The Qudi paper was published: http://doi.org/10.1016/j.softx.2017.02.001
 * Move everything to Qt5 only (no more Qt4 support) and pyqtgraph 0.10.0
 * Re-usable/configurable fit GUI components
 * Scienific notation input for PID GUI
 * Support for [Extensions](@ref extensions) (out-of-tree modules) 
 * Removed the fysom event parameter (usually called e) from on_activae and on_deactivate functions
 * Swabian Instruments TimeTagger / PulseStreamer hardware modules
 * Much faster savelogic
 * Remove 'Out' connectors, connection is now by module name only
 * Pulse analysis supports multiple methods
 * Predefined pulse sequences can now be imported from a custom path 
 (in addition to /logic/predefined_methods)
 * Module loading and unloading now definitely happens in the correct order
 * Locked modules are only deactivated after prompting the user

Config changes:
 * New optional parameter "additional_methods_dir" for SequenceGeneratorLogic
 * No more 'Out' connectors:

 Old style, produces lots of warnings:
 
 logic:
    counter:
        module.Class: 'counter_logic.CounterLogic'
        connect:
            counter1: 'mynicard.counter'
            savelogic: 'savelogic.savelogic'
    save:
        module.Class: 'save_logic.SaveLogic'
        win_data_directory: 'C:/Data'
        unix_data_directory: 'Data/'

 New style:
 
 logic:
    counter:
        module.Class: 'counter_logic.CounterLogic'
        connect:
            counter1: 'mynicard'
            savelogic: 'save'
    save:
        module.Class: 'save_logic.SaveLogic'
        win_data_directory: 'C:/Data'
        unix_data_directory: 'Data/'


## Release 0.7

Released on 01 Feb 2017.
Available at https://github.com/Ulm-IQO/qudi/releases/tag/v0.7 .

Changes/New features:

 * Overhaul of most used hardware modules, including
   * Error codes and failed hardware calls are caught and passed up to the logic
   * Updates of methods documentation in hardware modules and corresponding interfaces
 * Logic modules are now listening to the hardware return values and react accordingly
 * Introduction of update signals in most logic and GUI modules to ensure coherency of logic and GUI module information. So upon changing something in the GUI this module will emit an update signal which is connected to the logic module. The same works vice-versa if a script or something is changing values in logic modules.
 * Stability improvements to pulsed measurement analysis toolchain (pulse_extraction_logic and pulse_analysis_logic)
 * Changed SpinBoxes in pulsed_maingui BlockEditor, EnsembleOrganizer and SequenceOrganizer to scientific SpinBoxes enabling scientific number format and unit prefix input
 * Pulsed measurement data is saved properly now. Scientific number format was introduced to avoid problems with too few digits
 * Better pulsed_master_logic structure that allows now also for direct waveform/sequence generation on pulse generator devices (without writing files)
 * Heaps of changes/improvements regarding fitting in qudi. Big parts of fit_logic have been rewritten. It may be necessary to adapt custom scripts using fits
 * Confocal is now consequently using SI units (config change needed)
 * Confocal can now work from different count sources which are selectable (multichannel support) (config change needed)
 * Voltage range for NI card channels can be set independently for each channel (config change needed)

Config changes:

In order to update to the latest version of qudi one has to apply minor changes to the config file.

Change configuration settings for the ni_card module:

 * Replace "scanner_ao_channels" with "scanner_x_ao", "scanner_y_ao" and "scanner_z_ao".
   
     Example:
     
     scanner_x_ao: '/Dev1/AO0'  
     
     scanner_y_ao: '/Dev1/AO1'
     
     scanner_z_ao: '/Dev1/AO2'
     
     scanner_a_ao: '/Dev1/AO3'
     
   If you do not need the 4th axis, just leave it out.
   
 * You can either specify a voltage range for all axes:
 
   voltage_range:
   
    \- -10
    
    \- 10
    
 * or you have to specify one for each axis:
   
   x_voltage_range:
   
    \- -10
   
    \- 10
   
   y_voltage_range:
   
    \- -10
   
    \- 10
   
   z_voltage_range:
   
    \- 0
   
    \- 10
   
   a_voltage_range:
   
    \- -5
   
    \- 5

 * Change all distances in ni_card to meters; you can use exponential notation. For example:
   
   x_range:
   
    \- -100e-6
    
    \- 100e-6


The hardware file for Tektronix AWG70k series has been changed to use the pyvisa package for more robust and easy communication with the device:

 * The settings "awg_IP_address" and "awg_port" are not used anymore and have to be replaced with "awg_visa_address" and "awg_ip_address". For example:
```
   awg_visa_address: 'TCPIP0::AWG70K-38293801::inst0::INSTR'
   awg_ip_address: '192.168.1.3'
```

The Visa address can be obtained for example by the "Agilent connection expert" application.

## Release 0.6

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

