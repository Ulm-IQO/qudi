#Simple spectrometer interface {#simple-spectrometer-interface}

This interface let logic modules control the very basic functions of a spectrometer device.

## Methods

- `recordSpectrum`
    - Return a 2d array representing counts as a function of frequencies
    - Output : [array of float for frequencies, array of float for intensity (counts)]
- `setExposure`
    - Set the exposure time for future acquisitions
    - Input : 
        - float : exposure time in seconds
- `getExposure`
    - Get the current exposure time
    - Output : float : exposure time in seconds