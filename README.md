# qudi
QuDi is a suite of tools for operating laboratory experiments built around a confocal fluorescence microscope.
It was designed initially to perform *Qu*antum optics experiments on *Di*amond color centres,
but has utility in a far broader range of experimental contexts.

## Features
  * A modular and extendable architecture
  * Access to devices on other computers over network
  * XYZ piezo or galvo control for confocal microscopy via National Instruments X-Series devices
  * Position optimization for flourescent spots
  * Tracking of flourescent spots
  * Tektronix AWG support for pulsed microwave experiments
  * R&S SMIQ and SMR support for ODMR measurements
  * Getting spectra from the WinSpec32 spectroscopy software
  * Thorlabs APT motor control
  * Magnetic field alignment
  * etc.

## Citation
If you are publishing scientific results, mentioning Qudi in your methods decscription is the least you can do as good scientific practice.
We are preparing a paper about the software and DOIs for releases, which will make this process easier and more reliable.

## Documentation
User and code documentation about Qudi is located at http://qosvn2.physik.uni-ulm.de/qudi-docs .

## Collaboration
Feel free to register and add issues to our trac at http://qosvn2.physik.uni-ulm.de/trac/qudi .
and pull requests for improvements on github at https://github.com/Ulm-IQO/qudi .
The code in pull requests should be clean, PEP8-compliant and commented, as with every academic institution in Germany,
our resources in the area of software development are quite limited.

Do not expect help, debugging efforts or other support.

## License
Almost all parts of Qudi are licensed under GPLv3 (see LICENSE.txt) with the exception of some files
that originate from the Jupyter/IPython project.
These are under BSD license, check the file headers and the documentation folder.

Check COPYRIGHT.txt for a list of authors and the git history for their individual contributions.
