# Andor simple spectrometer hardware module {#simple-spectrometer-andor}

### Instruments

This module is supposed to be compatible with all Andor Cameras.
 It is very simple so it does not interact with Shamrock.
 
Tested with :
- Newton camera

### Interfaces

This hardware module follows the [simple] spectrometer interface.

### Use

One can use this module to acquire spectra with Qudi in a known configuration.

To use it, use Solis software to prepare the acquisition in a known configuration.

### Configuration file parameters

- `min_wavelength` - **required** - *float* - Wavelength in nm of the first pixel
- `min_wavelength` - **required** - *float* - Wavelength in nm of the last  pixel
- `default_exposure`- default : 1.0 - *float* - Default exposure time
- `temperature` - default -70 - *int* - Temperature the camera should be at


### Dependencies

This module use a wrapper around a .dll (Dynamic Link Library)
This wrapper is the pyandor library. It support both Windows and Linux. If you have trouble using this
wrapper, please check in the  `camera.py` the .dll path is correct.






