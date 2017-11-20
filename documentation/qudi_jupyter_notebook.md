# How to use the Qudi Jupyter Notebook {#jupyterkernel}

1. Install the Qudi Jupyter kernel
  * Ensure that your Anaconda environment or Python installation has
   up-to-date dependencies
  * In a terminal, go to the `core` folder in the `qudi` folder
  * Eventually do `activate qudi` to activate the conda environment
  * Do `python qudikernel.py install`
  * This should tell you where the kernel specification was installed
2. Configure Qudi
 * Ensure that your Qudi configuration file contains the following 
  entry or an equvalent configuration in the `global` section:

~~~~~~~~~~~~~
  remote_server:
    - address: 'localhost'
    - port: 12345
~~~~~~~~~~~~~

 * Ensure that your Qudi configuration file contains the following 
  entry in the `logic` section:

~~~~~~~~~~~~~
    kernellogic:
        module.Class: 'jupyterkernel.kernellogic.QudiKernelLogic'
        remoteaccess: True
~~~~~~~~~~~~~

3. Start the Jupyter notebook server
  * Run `activate qudi` to activate the conda environment
  * Run `jupyter notebook` or an equivalent, when starting from the
  Windows Start menu, be sure to pick the Jupyter notebook installed
  into the Qudi environment
  * Start Qudi with the configuration you checked before
  * Now, the 'New' menu should have a 'Qudi' entry and in a notebook, 
  the 'Kernel->Change kernel' menu should also have a qudi entry
  * If anything goes wrong, check that your firewall does not block
  the Qudi remote connections or the Jupyter notebook connections
