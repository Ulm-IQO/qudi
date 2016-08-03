# How to use and create tasks {#task-usage}

## General Task Concept

In order to create a task you can choose between 2 different categories.

**InterruptableTask** or **PrePostTask**

You have to inherit one of those classes (both are situated in `/logic/generic_tasks.py`) for your
tasks and re-implement the class specific methods for your needs. The tasks basically contain a
reference to the object you are aiming to manipulate.


**InterruptableTask** are those, which are used to perform the actual task. According to the name of
this class, you should design the task such, that it can be interrupted and stopped at any time.

To manage the behaviour of that, a finite state machine construction is used, which defines all
possible states of the InterruptableTask object **and** all valid state transitions (that is the
essence of a state machine!). The Graph below shows an ASM (algorithmic state machine) chart
of our underlying state machine:

[Graph InterruptableTask here]

**PrePostTask** are those which are done before or follow after the actual InterruptableTask.
The state machine description of those tasks are quite simple, as it can be seen in the Graph below.

[Graph PrePostTask here]

In general, the PrePostTasks are quite small steps (like e.g. tilting the mirror, switching on or
off of a device for the actual measurement).

## Task Implementation Concept

So now you have two possibilities to perform a manipulation.

1. Either the task itself just calls a method in the specific object and .
       then the object itself is responsible how the task will run,..
2. or you change and control every input/output value and construct (not
       only limited to one object) your desired task method.

For really basic and small tasks (which cannot or are not needed to be
separated into smaller tasks) the smartest way to implement task is via one
method, which can be called from one object. That idea is only restricted to the
scenario, if your task actions are limited to one object only! This very method
will handle then all needed changes within the object and will perform the
desired task. That idea will facilitate maintainability of the task, since it
only depends on the internal implementation of the addressed method. That makes
it traceable for the user.

As soon as your task will interact with many object (i.e. retrieve and pass
values from one object to the other and react on the obtained parameter) then
all the task implementation and object access will be done within the task and
not within the other objects, which the task is intended to control.

Think about an obvious/general way of how to return the data after a method,
i.e. the structure of the return value, maybe not just a bunch of elements in a
list, where you do not know, which element of a list is representing what. Think
of using pythons dictionaries, since you can assign to a generic and
understandable name to return values. Then you only have to fix yourself on a
proper keywords which you will use in the dict.

If the way you are calling and controlling this object is general, then other
people will potentially use it.


## Where are tasks saved?

Custom tasks are logic operations, and therefore saved in the folder `/logic/tasks` folder.
There you can also get an idea how implementation of possible tasks can look like.

## How to add your personal tasks in the config

Within a configuration file, a custom task configuration may look like that:

    tasklogic:
        module.Class: 'taskrunner.TaskRunner'
        tasks:
            dummytask:
                module: 'dummy'
                preposttasks: ['ppdummy']

            dummyinterruptor:
                module: 'dummy'
                pausetasks: ['dummytask']
                preposttasks: ['ppdummy2']

            ppdummy:
                module: 'prepostdummy'

            ppdummy2:
                module: 'prepostdummy'

            scannerLocationRefocus:
                module: 'refocus'
                preposttasks: ['fliplasermirror']
                pausetasks: ['scan', 'odmr']
                needsmodules:
                    optimizer: 'optimizerlogic'
                config:
                    initial: [1, 1, 1]

            fliplasermirror:
                module: 'flipmirror'
                needsmodules:
                    switchlogic: 'switch'
                config:
                    sequence: [('mydummyswitch1', 1, True), ('mydummyswitch1', 2, True), ('mydummyswitch2', 1, True)]

Your individual tasks can be defined below the `tasks` keyword. The naming
procedure is pretty similar to the working principle of our configuration files
([=> How to use a configuration file](@ref config-explanation).

    <identifier1>:
        module: '<module_name1>'
        preposttasks: ['<identifier2>']

    <identifier2>:
        module: '<module_name2>'

You choose a name `<identifier1>`, how the task should be called, and define with the keyword `module`
which task module you want to take. This module (a python file) with name
`<module_name1>` must be present in the \trunk\logic\task directory.



### Example for an InterruptableTask:

Within the file `<module_name1>.py` a class must exist with the name `Task`,
which inherits either the InterruptableTask or PrePostTask class. An example may
look like that:

    from logic.generic_task import InterruptableTask

    class Task(InterruptableTask):

        def __init__(self, name, runner, references, config):
            """ A task has the following constructor:

            @param str name: unique task name
            @param object runner: reference to the TaskRunner managing this task
            @param dict references: a dictionary of all required modules
            @param dict config: configuration dictionary
            """

            super().__init__(name, runner, references, config)
            print('Task {} added!'.format(self.name))
            print(self.config)

        def startTask(self)
            # Reimplement that!
            return

        def runTaskStep(self)
            # Reimplement that!
            return

        def pauseTask(self)
            # Reimplement that!
            return

        def resumeTask(self)
            # Reimplement that!
            return

        def cleanupTask(self)
            # Reimplement that!
            return


This example above must reimplement each method of the class
InterruptableTask. That would be right now the methods:

  - startTask,
  - runTaskStep,
  - pauseTask,
  - resumeTask,
  - cleanupTask.

The additional methods
  - checkExtraStartPrerequisites,
  - checkExtraPausePrerequisites

**can** be, but have not to be reimplemented, if no special requirements are going
to be set for that task. These methods are used to check, whether the present
task can be paused if it is in the running state.

Therefore, these methods provides you with e.g. an external checking procedure,
which you can implement for the specific task. Consequently the **return value**
has to be of **boolean** type, i.e. either `True` or `False`.

### Example of PrePostTask

The PrePostTask implementation is much simpler. An example of `<module_name2>`
might look like that:

    from logic.generic_task import PrePostTask

    class Task(PrePostTask):

        def __init__(self, name, runner, references, config):
            """ A task has the following constructor:

            @param str name: unique task name
            @param object runner: reference to the TaskRunner managing this task
            @param dict references: a dictionary of all required modules
            @param dict config: configuration dictionary
            """

            super().__init__(name, runner, references, config)
            print('PrePost init task {}'.format(name))
            print(self.config)

        def preExecute(self):
            # Reimplement that!
            return

        def postExecute(self):
            # Reimplement that!
            return

### The reference within a Task Class


### The config within a


## Example for the Confocal Optimizer Task



## Where are the task run?

All the tasks are handled by the Logic Module TaskRunner.py.


## How to use tasks in other logic

