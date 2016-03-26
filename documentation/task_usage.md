# How to use and create tasks {#task-usage}


In order to create a task you can choose between 2 different categories.

InterruptableTask, PrePostTask

You have to inherit one of those classes for your tasks and re-implement the
class specific methods for your needs. The tasks basically contain a reference
to the object you are aiming to manipulate. So now you have two possibilities to
perform a manipulation.

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




