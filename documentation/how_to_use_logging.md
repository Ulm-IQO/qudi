# How to use the logger in QuDi  {#logger_usage}

QuDi uses the [Python Logging Module](https://docs.python.org/3/library/logging.html)
from the Python Standard Library to manage all logging messages.

In general, the logging functionality is an essential feature for any software
developer, especially if the program grows in size and complexity.

## General functionality of the logger and why 'print()' is not always a good idea.

QuDi implements a core logger, which will carry together all child logger (from
the QuDi modules and from external module, who are using the logging module like
mentioned in the section [Logger in external file](#log_external)). The main
advantage of this procedure is that third party modules, which
are using the Standard Python Logger, are transferred to the core logger and
are logged too. This includes also self defined modules, which can be imported
into QuDi modules. That means there is no need for external modules to be
connected to QuDi to ensure the logging functionality, if the external modules
are tested and executed independent of QuDi.

Additionally, the manager GUI of QuDi will be able to show all (!) logging
messages from all files, which use the logging module.

That makes is easier and more convenient to use the logging module.

The print() function in python is only a better option whenever the main
application lies in **displaying a help** statement, which might often be the
case in command line applications and sometimes for on the fly scripts.

There are some arguments, why logging is better than print [[1](#lit_1)]:

- Events logged in included modules are automatically accessible via the root
  logger to your application’s logging stream, unless you filter them out.
- The log record, which is created with every logging event, contains readily
  available diagnostic information such as the file name, full path, function,
  and line number of the logging event.
- Logging can be selectively silenced by using the method
  logging.Logger.setLevel() or disabled by setting the attribute
  logging.Logger.disabled to True.

## <a name="log_external"> </a>Logger in external file

If you want to use the logging module in external file, which are not collected
to QuDi, then it is pretty easy to do that! Just add these following three lines
of code

    import logging
    logging.basicConfig(filename='logfile.log', filemode='w', level=logging.DEBUG)
    logger = logging.getLogger(__name__)

at the header of your script and the basic logger is ready to be used. Of course
you can adjust the name of the filename (here 'logfile.log') and the loglevel
(here logging.DEBUG) according to your needs. That will at least ensure, that a
file will be prepared with the name 'logfile.log', which contains all log
messages up to the level debug (i.e. basically every message).

Within the code, the logger can then be used like

    # (...) some code

    logger.info('A status message.')

    # (...) some code

    logger.warning('You should be careful!')

    # (...) some code

    logger.debug('Some infos which are less important.')

    # (...) some code

    logger.error('That is wrong. Correct that or do not do that again!')

    # (...) some code

    logger.critical('That is extremly dangerous and will seriouly harm the program or the devide!')

## How to use the logger within QuDi

Even before QuDi is started, the core logger of QuDi will be initialized and
will collect all the log messages and appearing exceptions upon the starting
procedure. I.e. if there appears an error in the configuration of the modules or
if modules are not present, which are needed at startup of QuDi, then the error
message(s) are collected in the root directory of qudi. Have a look in those
log files, if you encounter problems with QuDi, or if the QuDi Manager does not
even appear.

Each module in QuDi will by default have an attribute log, by which you can
access the logger of the specific module. If you take for instance the
CounterLogic, situated in the file logic/counter_logic.py, then you can use the
logger like

```python
# (...some import stuff...)

class CounterLogic(GenericLogic):

    # (...) some code
    def __init__(self, config, **kwargs):
        """ Create CounterLogic object with connectors.

        @param dict config: module configuration
        @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)

    def my_test_method(self):

        # some log methods.

        self.log.debug('That is an unneeded debug message.')
        self.log.info('That is an info message.')
        self.log.warning('That is a warning!')
```

## Location of the log file

The log file will be situated either in the root directory of QuDi or in the
current directory where the external module is loaded. With

```python
import os
print(os.getcwd())
```

you can find out the current directory, where the file is executed. There the
log file should be situated.


## Arguments passed to the logger

Unlike the build-in print method python, which accepts arbitrary input arguments,
the log methods only accept one argument. The input argument will be converted
to a string by default.
```python
import logging
logger = logging.getLogger(__name__)

import os
logger.info(os)
```
    >>> <module 'os' from '...\\Anaconda3\\lib\\os.py'>


## Logging Levels in QuDi

The logging used throughout qudi are the same defined in description of the logging package, which can be obtained [here](https://docs.python.org/3/library/logging.html#logging-levels).

| log in external module | log within QuDi | Numeric value           |
| ------------------- | :---------------------- |:---:|
| log.critical(...)   | self.log.critical(...)  |  50 |
| log.error(...)      | self.log.error(...)     |  40 |
| log.warning(...)    | self.log.warning(...)   |  30 |
| log.info(...)       | self.log.info(...)      |  20 |
| log.debug(...)      | self.log.debug(...)     |  10 |

A short note on the different log levels:

The purpose of the different log levels are almost self explaining.

Hoever, use the log level critical in very severe cases since that level should
be reserved for really bad event, like out of memory, disk is full or nuclear
meltdown,... . In many other cases the error level will serve well.

## Further information concerning the logging package

<a name="lit_1">[1]</a>: http://docs.python-guide.org/en/latest/writing/logging/#or-print <br />
<a name="lit_2">[2]</a>: https://docs.python.org/3/library/logging.html <br />
<a name="lit_3"></a>[3]: https://docs.python.org/3/howto/logging.html <br />