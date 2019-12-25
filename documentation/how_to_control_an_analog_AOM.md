# How to control an analog AOM with Qudi {#control-aom}

Acousto Optic Modulators (AOM) are generally used to create short laser pulse, on up to a few nanoseconds. By varying
the microwave power fed to the diffracting crystal, it is also possible to control the diffraction efficiency and so 
the final laser power.

The idea of the following scheme is to create a Qudi laser logic module representing the laser power effectively sent
to the experiment sample/objective/unicorn.

## Multi Layer detail

### Hardware layer - the AOM

Some AOM have an analog input channel that can be used to control diffraction efficiency. The idea here is to control
the by using a voltage analog output. Please note some AOM use 50 Ohms / 1V input, which correspond to a maximum current
of 20 mA, just above what some NI card can output.

### Analog output

To apply a voltage, one can use the *process_control_interface* implemented by a hardware module.

Example :
```
    analog_output:
        module.Class: 'some_module.Module'
```

### Non linearity

Applied voltage is generally directly fed to the MW amplification chain. One consequence is that diffraction efficiency
is non linear with applied power. To take this linearity into order, one can use the *process_control_modifier* 
interfuse. This interfuse uses two X and Y vectors to change a power control value to a non linear voltage control
value. Configuration can be done easily with aom logic (cf. bellow)

```
    power_to_volt_modifier:
        module.Class: 'interfuse.process_control_modifier.ProcessControlModifier'
        connect:
            hardware: 'analog_output'
        new_unit: ['', 'Relative power']
```

### Feedback - the power meter

To calibrate our modifier, one need a power meter as a hardware module with *process_interface*.

### Control laser interfuse

This interfuse creates a virtual hardare laser which power and state can be interacted easily by the laser logic.

```
    control_laser_interfuse:
        module.Class: 'interfuse.control_value_laser_interfuse.Interfuse'
        connect:
            control: 'power_to_volt_modifier'
```

### Laser logic and GUI

One can use usual laser logic and GUI to set the power in a convenient manner.

```
    laserlogic:
        module.Class: 'laser_logic.LaserLogic'
        connect:
            laser: 'control_laser_interfuse'
```

### AOM logic and GUI

The final step is to use a specific module that orchestrate everything so that configuration is easy. This is 
aom_logic.

```
    aomlogic:
        module.Class: 'aom_logic.AomLogic'
        connect:
            voltage_output: 'analog_output'
            power_input: 'power_meter'
            control_laser_interfuse: 'control_laser_interfuse'
            output_modifier: 'power_to_volt_modifier'
            laser: 'laserlogic'
            savelogic: 'savelogic'
```
