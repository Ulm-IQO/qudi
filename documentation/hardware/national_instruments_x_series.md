# National Instruments X Series Data Acquisition Cards {#nidaq-x-series}

## Introduction
A National Instruments device that can count, record analog signals and control analog scanners 
and microvave generators

**!!!!!! 
This module only works with NI USB 63XX, NI PCIe 63XX and NI PXIe 63XX devices
Other devices do not have enough hardware counters or the counters do not support
all required functionality.
!!!!!!!**

Basic procedure how the NI card is configured:
  * At first you have to define a channel, where the APD clicks will be
    received. That can be any PFI input, which is specified to record TTL
    pulses.
  * Then the counter channels have to be configured.
  * One counter channel serves as a timing device, i.e. basically a clock
    which runs at a certain given frequency.
  * The second counter channel will be used as a counting device,
    which will, dependent on the clock, count within the clock interval. The faster
    the clock channel is configured, the smaller is the counting
    interval and the less counts per clock periode you will count.

[Text Based NI-DAQmx Data Acquisition Examples](http://www.ni.com/example/6999/en/#ANSIC)

## Terminology

Explanation of the terminology, which is used in the NI Card and useful to
know in for working with our implementation:

#### Hardware-Timed Counter Tasks:

Use hardware-timed counter input operations to drive a control loop. A
really good explanation can be found in:

http://zone.ni.com/reference/en-XX/help/370466V-01/mxcncpts/controlappcase4/

#### Terminals:

A terminal is a named location where a signal is either generated
(output or produced) or acquired (input or consumed). A terminal that
can output only one signal is often named after that signal. A terminal
with an input that can be used only for one signal is often named after
the clock or trigger that the signal is used for. Terminals that are
used for many signals have generic names such as RTSI, PXITrig, or PFI.

http://zone.ni.com/reference/en-XX/help/370466W-01/mxcncpts/terminal/
http://zone.ni.com/reference/en-XX/help/370466V-01/mxcncpts/termnames/

##### Ctr0Out, Ctr1Out, Ctr2Out, Ctr3Out
Terminals at the I/O connector where the output of counter 0,
counter 1, counter 2, or counter 3 can be emitted. You also can use
Ctr0Out as a terminal for driving an external signal onto the RTSI bus.

##### Ctr0Gate, Ctr1Gate, Ctr2Gate, Ctr3Gate
Terminals within a device whose purpose depends on the application.
Refer to Counter Parts in NI-DAQmx for more information on how the gate
terminal is used in various applications.

##### Ctr0Source, Ctr1Source, Ctr2Source, Ctr3Source
Terminals within a device whose purpose depends on the application.
Refer to Counter Parts in NI-DAQmx for more information on how the
source terminal is used in various applications.

##### Ctr0InternalOutput, Ctr1InternalOutput, Ctr2InternalOutput, Ctr3InternalOutput
Terminals within a device where you can choose the pulsed or toggled
output of the counters. Refer to Counter Parts in NI-DAQmx (or MAX)
for more information on internal output terminals.

#### Task State Model:
NI-DAQmx uses a task state model to improve ease of use and speed up
driver performance. Have a look at

http://zone.ni.com/reference/en-XX/help/370466V-01/mxcncpts/taskstatemodel/

**Short explanation:**
The task state model consists of five states
  * Unverified
  * Verified
  * Reserved
  * Committed
  * Running
  
You call the Start Task function/VI, Stop Task function/VI, and
Control Task function/VI to transition the task from one state to
another. The task state model is very flexible. You can choose to
interact with as little or as much of the task state model as your
application requires.

#### Device limitations:
Keep in mind that ONLY the X-series of the NI cards is capable of doing
a Counter Output Pulse Frequency Train with finite numbers of samples
by using ONE internal device channel clock (that is the function
`DAQmxCreateCOPulseChanFreq` or `CO Pulse Freq` in Labview)! All other card
series have to use two counters to generate that!
Check out the description of NI which tells you 
[How Many Counters Does Each Type of Counter Input or Output Task Take](http://digital.ni.com/public.nsf/allkb/9D1780F448D10F4686257590007B15A8).

The code in Qudi tested with NI 6323 and NI 6229, where the first one is
an X-series device and the latter one is a Low-Cost M Series device.
With the NI 6229 it is not possible at all to perform the scanning
task unless you have two of that cards. The limitation came from a lack
of internal counters.
The NI 6323 was taken as a basis for this hardware module and thus all
the function are working on that card.
 
## Configuration

There are quite a few options for setting up a National instruments card.

Here is an example for a NI6323 card with the name Dev1.

````yaml
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
````

### Parameter explanation

``clock_channel``: A counter channel that will generate the clock for the counter functionality.
Required when using the CounterInterface of this module.

``scanner_clock_channel``: a counter channel that will generate the pixel clock for confocal and ODMR scans

``photon_sources``: connectors where pulse generating devices can be connected, like avalance photo diodes
Required when using the CounterInterface of this module.

``counter_channels``: counter channels that are used to count the pulses from ``photon_sources`` for
counting cunctionality

``counter_ai_channels``: optional analog inputs that are treated like ``counter_channels`` for counting functionality

``scanner_counter_channels``: counter channels hat are used to record confocal or ODMR scans

``scanner_ai_channels``: optional analog inputs that are used like ``scanner_counter_channels``

``scanner_ao_channels``: analog outputs that are used to control a microscope scanner, one for each axis

``scanner_position_ranges``: the real-world positions of the microscope scan ranges, one pair for each axis, in meters

``scanner_voltage_ranges``: voltages that correspond the extreme values of the microscope scanner ranges,
 one pair for each axis
 
``default_samples_number``: 
 
``default_clock_frequency``: the standard frequency for the counter sample clock
 
``default_scanner_clock_frequency``:  the standard frequency for the microscope scanner or ODMR pixel clock
 
``gate_in_channel``: input for gating the counting channels
 
``counting_edge_rising``: whether to count rising or falling edges
 
``odmr_trigger_channel``: output for the trigger pulse for ODMR microwave sources
 
``pixel_clock_channel``: optional output for the confocal pixel clock