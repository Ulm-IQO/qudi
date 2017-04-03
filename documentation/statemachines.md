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

### State transition functions

Do not declare these transition function names in anything derived from Base, that will lead to 
unexpected behaviour!

* activate:    
  * deactivated -> idle
* deactivate:
  * idle -> deactivated
  * running -> deactivated
  * locked -> deactivated (manager makes sure this only happens after prompting the user)
* run:
  * idle -> running
* stop:
  * running -> idle
* lock:
  * idle -> locked
  * running -> locked
* unlock:
  * locked -> idle
* runlock:
  * locked -> running

## Default event handler and fysom event objects

In a module the default event handler called after the state has transitioned to activate or deactivate are the methods called `on_activate` and `on_deactivate`. Both methods don't take any parameters as default. For debugging purposes it is sometimes useful to access to the fysom event object. This is possible by defining new callback methods in the constructor:

```python
def __init__(self, **kwargs):
    super().__init__(
        self,
        callbacks={'onactivate': self.on_activate}, 
        **kwargs)
```

and adding the fysom event object as parameter to the event handler:

```python
def on_activate(self, e):
    do_something_with_fysom_event_object(e)
```

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

