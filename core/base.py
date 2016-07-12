# -*- coding: utf-8 -*-
"""
This file contains the QuDi module base class.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from pyqtgraph.Qt import QtCore
from fysom import Fysom # provides a final state machine
from collections import OrderedDict

import numpy as np
import os
import sys
import traceback

class Base(QtCore.QObject, Fysom):
    """
    Base class for all loadable modules

    * Ensure that the program will not die during the load of modules in any case,
      and therefore do nothing!!!
    * Initialize modules
    * Provides a self identification of the used module
    * Output redirection (instead of print)
    * Provides a self de-initialization of the used module
    * Reload the module with code changes
    * Get your own configuration (for save)
    * Get name of status variables
    * Get status variables
    * Reload module data (from saved variables)
    """

    sigStateChanged = QtCore.Signal(object)  #(module name, state change)
    sigLogMessage = QtCore.Signal(object)
    _modclass = 'base'
    _modtype = 'base'
    _in = dict()
    _out = dict()

    def __init__(self, manager, name, configuration={}, callbacks={}, **kwargs):
        """ Initialise Base class object and set up its state machine.

          @param object self: tthe object being initialised
          @param object manager: the manager object that
          @param str name: unique name for this object
          @param dict configuration: parameters from the configuration file
          @param dict callbacks: dictionary specifying functions to be run on state machine transitions

        """

        # Qt signal/slot capabilities
        QtCore.QObject.__init__(self)

        default_callbacks = {
            'onactivate': self.on_activate,
            'ondeactivate': self.on_deactivate}
        default_callbacks.update(callbacks)

        # State machine definition
        # the abbrivations for the event list are the following:
        #   name:   event name,
        #   src:    source state,
        #   dst:    destination state
        _baseStateList = {
            'initial': 'deactivated',
            'events': [
                {'name': 'activate',    'src': 'deactivated',   'dst': 'idle' },
                {'name': 'deactivate',  'src': 'idle',          'dst': 'deactivated' },
                {'name': 'deactivate',  'src': 'running',       'dst': 'deactivated' },
                {'name': 'run',         'src': 'idle',          'dst': 'running' },
                {'name': 'stop',        'src': 'running',       'dst': 'idle' },
                {'name': 'lock',        'src': 'idle',          'dst': 'locked' },
                {'name': 'lock',        'src': 'running',       'dst': 'locked' },
                {'name': 'block',       'src': 'idle',          'dst': 'blocked' },
                {'name': 'block',       'src': 'running',       'dst': 'blocked' },
                {'name': 'locktoblock', 'src': 'locked',        'dst': 'blocked' },
                {'name': 'unlock',      'src': 'locked',        'dst': 'idle' },
                {'name': 'unblock',     'src': 'blocked',       'dst': 'idle' },
                {'name': 'runlock',     'src': 'locked',        'dst': 'running' },
                {'name': 'runblock',    'src': 'blocked',       'dst': 'running' }
            ],
            'callbacks': default_callbacks
        }

        # Initialise state machine:
        Fysom.__init__(self, _baseStateList)

        # add connection base
        self.connector = OrderedDict()
        self.connector['in'] = OrderedDict()
        for con in self._in:
            self.connector['in'][con] = OrderedDict()
            self.connector['in'][con]['class'] = self._in[con]
            self.connector['in'][con]['object'] = None

        self.connector['out'] = OrderedDict()
        for con in self._out:
            self.connector['out'][con] = OrderedDict()
            self.connector['out'][con]['class'] = self._out[con]

        self._manager = manager
        self._name = name
        self._configuration = configuration
        self._statusVariables = OrderedDict()
        # self.sigStateChanged.connect(lambda x: print(x.event, x.fsm._name))

    def on_activate(self, e):
        """ Method called when module is activated. If not overridden
            this method returns an error.

        @param object e: Fysom state change descriptor
        """
        self.logMsg('Please implement and specify the activation method for '
                '{0}.'.format(self.__class__.__name__), msgType='error')

    def on_deactivate(self, e):
        """ Method called when module is deactivated. If not overridden
            this method returns an error.

        @param object e: Fysom state change descriptor
        """
        self.logMsg('Please implement and specify the deactivation method '
                '{0}.'.format(self.__class__.__name__), msgType='error')

    # Do not replace these in subclasses
    def onchangestate(self, e):
        """ Fysom callback for state transition.

        @param object e: Fysom state transition description
        """
        self.sigStateChanged.emit(e)

    def getStatusVariables(self):
        """ Return a dict of variable names and their content representing the module state for saving.

        @return dict: variable names and contents.

        """
        return self._statusVariables

    def setStatusVariables(self, variableDict):
        """ Give a module a dict of variable names and their content representing the module state.

          @param OrderedDict dict: variable names and contents.

        """
        if not isinstance(variableDict, (dict, OrderedDict)):
            self.logMsg('Did not pass a dict or OrderedDict to setStatusVariables in {0}.'.format(self.__class__.__name__), msgType='error')
            return
        self._statusVariables = variableDict

    def getState(self):
        """Return the state of the state machine implemented in this class.

          @return str: state of state machine

          Valid return values are: 'deactivated', 'idle', 'running', 'locked', 'blocked'
        """
        return self.current

    def getConfiguration(self):
        """ Return the configration dictionary for this module.

          @return dict: confiuration dictionary

        """
        return self._configuration

    def getConfigDirectory(self):
        """ Return the configuration directory for the manager this module belongs to.

          @return str: path of configuration directory

        """
        return self._manager.configDir

    def logMsg(self, message, **kwargs):
        """Creates a status message method for all child classes.

          @param string message: the text of the log message
        """
        self.sigLogMessage.emit(('{0}.{1}: {2}'.format(self._modclass, self._modtype, message), kwargs))

    def logExc(self, *args, **kwargs):
        """Calls logMsg, but adds in the current exception and callstack.

          @param list args: arguments for logMsg()
          @param dict kwargs: dictionary containing exception information.

        Must be called within an except block, and should only be called if the
        exception is not re-raised.
        Unhandled exceptions, or exceptions that reach the top of the callstack
        are automatically logged, so logging an exception that will be
        re-raised can cause the exception to be logged twice.
        Takes the same arguments as logMsg.
        """
        kwargs['exception'] = sys.exc_info()
        kwargs['traceback'] = traceback.format_stack()[:-2] + ["------- exception caught ---------->\n"]
        self.logMsg(*args, **kwargs)

    @staticmethod
    def identify():
        """ Return module id.

          @return dict: id dictionary with modclass and modtype keys.
        """
        return {moduleclass: _class, moduletype: _modtype}

    def get_main_dir(self):
        """Returns the absolut path to the directory of the main software.

             @return string: path to the main tree of the software

        """
        mainpath=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
        self.logMsg('Filepath of the main tree was called', msgType='status',
                    importance=0)

        return mainpath
 #            print("PAth of Managerfile: ", os.path.abspath(__file__))


    def get_home_dir(self):
        """ Returns the path to the home directory, which should definitely
            exist.
            @return string: absolute path to the home directory
        """
        return os.path.abspath(os.path.expanduser('~'))

    def get_unit_prefix_dict(self):
        """ Return the dictionary, which assigns the prefix of a unit to its
            proper order of magnitude.
        @return dict: keys are string prefix and items are magnitude values.
        """

        unit_prefix_dict = {'f':1e-15, 'p':1e-12, 'n': 1e-9, 'micro':1e-6,
                            'm':1e-3, '':1, 'k':1e3, 'M':1e6, 'G':1e9,
                            'T':1e12, 'P':1e15}
        return unit_prefix_dict

    def create_formatted_output(self, param_dict, default_digits=5):
        """ Display a parameter set nicely.

        @param dict param: dictionary with entries being again dictionaries
                           with two needed keywords 'value' and 'unit' and one
                           optional keyword 'error'. Add the proper items to the
                           specified keywords.
                           Note, that if no error is specified, no proper
                           rounding (and therefore displaying) can be
                           guaranteed.

        @param int default_digits: optional, the default digits will be taken,
                                   if the rounding procedure was not successful
                                   at all. That will ensure at least that not
                                   all the digits are displayed.

        @return str: a string, which is nicely formatted.

        Note: If you want that the values are displayed in a certain order, then
              use OrderedDict from the collections package.

        Example of a param dict:
            param_dict = {'Rabi frequency': {'value':123.43,   'error': 0.321,  'unit': 'MHz'},
                          'ODMR contrast':  {'value':2.563423, 'error': 0.523,  'unit': '%'},
                          'Fidelity':       {'value':0.783,    'error': 0.2222, 'unit': ''}}

            If you want to access on the value of the Fidelity, then you can do
            that via:
                param_dict['Fidelity']['value']
            or on the error of the ODMR contrast:
                param_dict['ODMR contrast']['error']


        """

        output_str = ''
        for entry in param_dict:
            if param_dict[entry].get('error') is None:
                output_str += '{0} : {1} {2} \n'.format(entry,
                                                        param_dict[entry]['value'],
                                                        param_dict[entry]['unit'])
            else:
                value, error, digit = self.round_value_to_error(param_dict[entry]['value'], param_dict[entry]['error'])

                # check if the error is so big that the rounded value will
                # become just zero. In that case, output at least 5 digits of
                # the actual value and not the complete value, just to have
                # some sort of a display:
                if np.isclose(value, 0.0) or np.isnan(error) or np.isclose(error, 0.0):

                    # catch the rare case, when the value is almost exact zero:
                    if np.isclose(param_dict[entry]['value'], 0.0):

                        if np.isnan(error) or np.isclose(error, 0.0):

                            # give it up, value is zero, and error is an invalid
                            # number, just pass everything to the output:
                            value = param_dict[entry]['value']
                            error = param_dict[entry]['error']
                            digit = -1
                        else:

                            # if just the value is zero, try to estimate the
                            # digit via the error:
                            digit = -(int(np.log10(abs(param_dict[entry]['error'])))-default_digits)
                            value = param_dict[entry]['value']
                            error = param_dict[entry]['error']
                    else:
                        # just output the specified default_digits of the value
                        # if fit was not working properly:
                        digit = -(int(np.log10(abs(param_dict[entry]['value'])))-default_digits)
                        value = param_dict[entry]['value']

                if digit < 0:
                    output_str += '{0} : {1} \u00B1 {2} {3} \n'.format(entry,
                                                                       value,
                                                                       error,
                                                                       param_dict[entry]['unit'])
                else:
                    output_str += '{0} : {1:.{4}f} \u00B1 {2:.{4}f} {3} \n'.format(entry,
                                                                                 value,
                                                                                 error,
                                                                                 param_dict[entry]['unit'],
                                                                                 digit)
        return output_str

    def round_value_to_error(self, value, error):
        """ The scientifically correct way of rounding a value according to an error.

        @param float or int value: the measurement value
        @param float or int error: the error for that measurement value

        @return tuple(float, float, int):
                    float value: the rounded value according to the error
                    float error: the rounded error
                    int rounding_digit: the digit, to which the rounding
                                        procedure was performed. Note a positive
                                        number indicates the position of the
                                        digit right from the comma, zero means
                                        the first digit left from the comma and
                                        negative numbers are the digits left
                                        from the comma. That is a convention
                                        which is used in the native round method
                                        and the method numpy.round.

        Note1: the input type of value or error will not be changed! If float is
               the input, float will be the output, same applies to integer.

        Note2: This method is not returning strings, since each display method
               might want to display the rounded values in a different way.
               (in exponential representation, in a different magnitude, ect.).

        Note3: This function can handle an invalid error, i.e. if the error is
               zero or NAN.

        Procedure explanation:
        The scientific way of displaying a measurement result in the presents of
        an error is applied here. It is the following procedure:
            Take the first leading non-zero number in the error value and check,
            whether the number is a digit within 3 to 9. Then the rounding value
            is the specified digit. Otherwise, if first leading digit is 1 or 2
            then the next right digit is the rounding value.
            The error is rounded according to that digit and the same applies
            for the value.

        Example 1:
            x_meas = 2.05650234, delta_x = 0.0634
                => x =  2.06 +- 0.06,   (output: (2.06, 0.06, 2)    )

        Example 2:
            x_meas = 0.34545, delta_x = 0.19145
                => x = 0.35 +- 0.19     (output: (0.35, 0.19, 2)    )

        Example 3:
            x_meas = 239579.23, delta_x = 1289.234
                => x = 239600 +- 1300   (output: (239600.0, 1300.0, -2) )

        Example 4:
            x_meas = 961453, delta_x = 3789
                => x = 961000 +- 4000   (output: (961000, 4000, -3) )

        """

        # check if error is zero, since that is an invalid input!
        if np.isclose(error, 0.0) or np.isnan(error):
            self.logMsg('Cannot round to the error, since either a zero error '
                        'value was passed for the number {0}, or the error is '
                        'NaN: Error value: {1}. '.format(value, error),
                        msgType='warning')

            # set the round digit to float precision
            round_digit = -12

            return value, error, round_digit

        # error can only be positive!
        log_val = np.log10(abs(error))

        if log_val < 0:
            round_digit = -(int(log_val)-1)
            first_err_digit = str(np.round(error, round_digit))[-1]

        else:
            round_digit = -(int(log_val))
            first_err_digit = str(np.round(error, round_digit))[0]

        if first_err_digit== '1' or first_err_digit == '2':
            round_digit = round_digit + 1

        # I do not why the round routine in numpy produces sometimes an long
        # series of numbers, even after rounding. The internal round routine
        # works marvellous, therefore this is take as the proper output:

        return round(value, round_digit), round(error, round_digit), round_digit

