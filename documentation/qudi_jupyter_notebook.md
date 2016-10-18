# How to use the Qudi Jupyter Notebook {#jupyterkernel}

1. Install the Qudi Jupyter kernel
  * Ensure that your Anaconda environment or Python installation has
   up-to-date dependencies
  * In a terminal, go to the `tools` folder in the `qudi` folder
  * Eventually do `activate qudi` to activate the conda environment
  * Do `python qudikernel.py install`
  * This should tell you where the kernel specification was installed
2. Configure Qudi
  * Ensure that your Qudi configuration file contains the following 
  entry in the `logic` section:

~~~~~~~~~~~~~
    kernellogic:
        module.Class: 'jupyterkernel.kernellogic.QudiKernelLogic'
        remoteaccess: True
~~~~~~~~~~~~~

3. Start the Jupyter notebook server
  * Run `jupyter notebook` or an equivalent
  * Start Qudi with the configuration you checked before
  * Now, the 'New' menu should have a 'Qudi' entry and in a notebook, 
  the 'Kernel->Change kernel' menu should also have a qudi entry
  * If anything goes wrong, check that your firewall does not block
  the Qudi remote connections or the Jupyter notebook connections
