# Sensor, control and PID {#pid_features}

Qudi provide several features to measure and control a parameter of a setup via setpoint or PID.

### Vocabulary

If you're not familiar with PID terminology, here are the basic terms.

For illustration purpose, let's imagine that the parameter you wan to control is the room temperature.
 
 - The **Process variable** is the value measured by a sensor, it is for example the measured temperature
 - The **Setpoint value** is the value the process variable should try to achieve. In the example it is the
 temperature that you program.
 - The **Control value** is the value of the process that tries to regulate the precess variable, for example 
 the heater power.
 
### Qudi's interfaces

Sometime, you just want to plot a measurement curve to monitor the setup, sometime you have more control,
to ease the programmer's life, Qudi has several layers that work together :
- A process_interface for a simple process variable
- A setpoint_interface for a simple setpoint value
- A setpoint_controller_interface built on top of theses two to make a basic controller
- A process_control_interface for a simple process value command
- (Work in progress) A general PID interface built on top of the three previous simple interfaces
 
 