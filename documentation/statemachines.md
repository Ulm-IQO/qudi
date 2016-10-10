# State machines with Fysom {#statemachines}

Fysom is a Python package that allows the effortless creation of state machines with callbacks.

## Module state machine

Each Qudi module contains, via the Base class, a state machine that governs some of its behaviour
regarding activation and deactivation.

### States
The states are:

* deactivated
* idle
* running
* locked
* blocked

### State transition functions

Do not declare these transition function names in anything derived from Base, that will lead to 
unexpected behaviour!

* activate:    
  * deactivated -> idle
* deactivate:
  * idle -> deactivated
  * running -> deactivated
* run:
  * idle -> running
* stop:
  * running -> idle
* lock:
  * idle -> locked
  * running -> locked
* block:
  * idle -> blocked
  * running -> blocked
* locktoblock:
  * locked -> blocked
* unlock:
  * locked -> idle
* unblock:
  * blocked -> idle
* runlock:
  * locked -> running
* runblock:
  * blocked -> running

## Interruptable task state machine


InterruptableTask represents a task in a module that can be safely executed by checking preconditions
and pausing other tasks that are being executed as well.
The task can also be paused, given that the preconditions for pausing are met.

State diagram:

~~~~~~~~~~~~~
stopped -> starting -----------> running ---------> finishing -*
   ^          |            _______|   ^_________               |
   |<---------*            v                   |               v
   |                   pausing -> paused -> resuming           |
   |                      |                    |               |
   ^                      v                    v               |
   |-------------<--------|----------<---------|--------<-------
~~~~~~~~~~~~~

Each state has a transition state that allow for checks, synchronizatuion and for parts of the task
to influence its own execution via signals.
This also allows the TaskRunner to be informed about what the task is doing and ensuring that a task
is executed in the correct thread.

## PrePost task state machine

Fill in later

