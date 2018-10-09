# How to get started  {#get-started}

This article is a attempt at guiding new users through the process of installing, understanding and using Qudi.

## Installation on a test machine

If you are new to Qudi, you may want to try it out in a demo environment on your own computer.

Luckily, the way Qudi is built let you have a look at most user interfaces and tools even if your computer isn't really
connected to real instruments. There even are some module that try to simulate what real instruments on a real setup
would give.

#### Installation

To install Qudi on your test machine, you can follow the dedicated [installation guide](@ref installation).

The default configuration file `config/example/default.cfg` gives access to most GUI modules. You can try them without
worrying of breaking anything.

## Installation on the setup machine

Now that you have explored the basic features of Qudi and are convinced to use it in you lab, you need to install Qudi
on a machine that have access to the instruments.

The basic installation is exactly the same as for the test machine.

Once you have done this, you will need to configure Qudi to your requirements.
It is best to create a `config/local` directory to hold your site-specific config files.
An `app_status` folder is created in the directory of the active config file, and this 
directory holds saved status variables that allow Qudi to restore to the previous state
after shutdown. Some modules may have different values (number of channels, etc) for different
config files, and so it is important to have a subdirectory for each config file.

#### Basic Configuration

The Qudi suite was originally built around a NI card controlled confocal fluorescence microscope experiments. 
For this reason, let's assume your setup is similar.

For a detailed explanation on the config file, please refer to the dedicated article 
[How to use and understand a config file](@ref config-explanation)

##### The setup

A confocal fluorescence microscope can be summarized as a detector of fluorescence (single photon or light intensity)
 and a moving device to move the this detector relatively to a sample. This could be piezo scanners, a steering mirror,
  piezo steppers, or even a combination of any of them.

##### Qudi modules

As a user, you interact with the GUI modules. Here we focus on two of them : `counter` and `confocal`.
You can find detailed documentation in [Counter GUI] and [Confocal GUI](@ref confocalgui)

This GUI modules need to be connected to their logic module, which in turn need some hardware module preferably through 
a dedicated interface.

For now, the `hardware/national_instruments_x_series` file used with a NI Card is the main hardware module and a lot 
the Qudi code is build around it. In future versions, the separation between hardware and logic should be refined.

For now, you can refer to [National Instrument X Series Hardware] to understand how to configure this hardware module.

## Other modules

Qudi now has a lot of other modules and capabilities. We won't go through all of them here, we're just going to cite
some of them. To find out about all of them, you will need to go through the documentation and might need to dive into
the Python code.
- [ODMR] (Continous wave, sweep or list)
- [Microwave pulse generator]
- [Spectroscoy]

## Then what ?

You might be lucky enough to find all the tools you need to conduct you experiment. But there's a good chance you will
need something that haven't been developed before. 

This may be just a hardware module to control a new instrument, a new button in a GUI or a whole new hardware/logic/GUI
tool.

In that case, you will need to go even deeper in the code and you might want to share your hard work. Please refer to 
[How to participate] page to find everything you need to know about collaborating.
 

