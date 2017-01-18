# -*- coding: utf-8 -*-
"""
This module handles the saving of data.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from collections import OrderedDict
from cycler import cycler
import logging
import os
import sys
import inspect
import time
import numpy as np

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.util import units

class DailyLogHandler(logging.FileHandler):
    """
    log handler which uses savelogic's get_daily_directory to log to a
    file called base_filename

    @param base_filename str: The base filename of the log file in the daily
                              directory. The filename will be datetime
                              formatted. E.g. '%Y%m%d-%H%M%S-qudi.log'.
    @param savelogic object: the savelogic
    """

    def __init__(self, base_filename, savelogic):
        self._savelogic  = savelogic
        self._base_filename = base_filename
        # get current directory
        self._current_directory = savelogic.get_daily_directory()
        self._current_time = time.localtime()
        super().__init__(self.filename)

    @property
    def current_directory(self):
        """
        Returns the currently used directory
        """
        return self._current_directory

    @property
    def filename(self):
        return os.path.join(self._current_directory,
                time.strftime(self._base_filename,
                    self._current_time))

    def emit(self, record):
        """
        Emits a record. It checks if we have to rollover to the next daily
        directory before it emits the record.

        @param record struct: a log record
        """
        # check if we have to rollover to the next day
        now = time.localtime()
        if (now.tm_year != self._current_time.tm_year
                or now.tm_mon != self._current_time.tm_mon
                or now.tm_mday != self._current_time.tm_mday):
            # we do
            # close file
            self.flush()
            self.close()
            # remember current time
            self._current_time = now
            # get the new directory, but avoid recursion because
            # get_daily_directory uses the log itself
            level = self.level
            self.setLevel(100)
            new_directory = self._savelogic.get_daily_directory()
            self.setLevel(level)
            # open new file in new directory
            self._current_directory = new_directory
            self.baseFilename = self.filename
            self._open()
            super().emit(record)
        else:
            # we don't
            super().emit(record)



class FunctionImplementationError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SaveLogic(GenericLogic):

    """
    A general class which saves all kinds of data in a general sense.
    """

    _modclass = 'savelogic'
    _modtype = 'logic'

    # declare connectors
    _out = {'savelogic': 'SaveLogic'}

    # Matplotlib style definition for saving plots
    mpl_qd_style = {'axes.prop_cycle': cycler('color', ['#1f17f4',
                                                        '#ffa40e',
                                                        '#ff3487',
                                                        '#008b00',
                                                        '#17becf',
                                                        '#850085'
                                                        ]
                                              ) + cycler('marker', ['o', 's', '^', 'v', 'D', 'd']),
                    'axes.edgecolor': '0.3',
                    'xtick.color': '0.3',
                    'ytick.color': '0.3',
                    'axes.labelcolor': 'black',
                    'font.size': '14',
                    'lines.linewidth': '2',
                    'figure.figsize': '12, 6',
                    'lines.markeredgewidth': '0',
                    'lines.markersize': '5',
                    'axes.spines.right': True,
                    'axes.spines.top': True,
                    'xtick.minor.visible': True,
                    'ytick.minor.visible': True,
                    'savefig.dpi': '180'
                    }

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.lock = Mutex()

        self.log.info('The following configuration was found.')

        # name of active POI, default to empty string
        self.active_poi_name = ''

        # Some default variables concerning the operating system:
        self.os_system = None
        self.default_unix_data_dir = 'Data'
        self.default_win_data_dir = 'C:/Data/'

        # Chech which operation system is used and include a case if the
        # directory was not found in the config:
        if sys.platform in ('linux', 'darwin'):
            self.os_system = 'unix'
            if 'unix_data_directory' in config:
                self.data_dir = config['unix_data_directory']
            else:
                self.data_dir = self.default_unix_data_dir

        elif 'win32' in sys.platform or 'AMD64' in sys.platform:
            self.os_system = 'win'
            if 'win_data_directory' in config.keys():
                self.data_dir = config['win_data_directory']
            else:
                self.data_dir = self.default_win_data_dir
        else:
            self.log.error('Identify the operating system.')

        # start logging into daily directory?
        if 'log_into_daily_directory' in config.keys():
            if not isinstance(config['log_into_daily_directory'], bool):
                self.log.warning('log entry in configuration is not a '
                        'boolean. Falling back to default setting: False.')
                self.log_into_daily_directory = False
            else:
                self.log_into_daily_directory = config[
                        'log_into_daily_directory']
        else:
            self.log.warning('Configuration has no entry log. Falling back '
                    'to default setting: False.')
            self.log_into_daily_directory = False
        self._daily_loghandler = None

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self, e=None):
        """ Definition, configuration and initialisation of the SaveLogic.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look
                         in the Base Class). This object contains the passed
                         event the state before the event happens and the
                         destination of the state which should be reached
                         after the event has happen.
        """
        if self.log_into_daily_directory:
            # adds a log handler for logging into daily directory
            self._daily_loghandler = DailyLogHandler(
                    '%Y%m%d-%Hh%Mm%Ss-qudi.log', self)
            self._daily_loghandler.setFormatter(logging.Formatter(
                '%(asctime)s %(name)s %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'))
            self._daily_loghandler.setLevel(logging.DEBUG)
            logging.getLogger().addHandler(self._daily_loghandler)
        else:
            self._daily_loghandler = None

    def on_deactivate(self, e=None):
        if self._daily_loghandler is not None:
            # removes the log handler logging into the daily directory
            logging.getLogger().removeHandler(self._daily_loghandler)

    @property
    def dailylog(self):
        """
        Returns the daily log handler.
        """
        return self._daily_loghandler

    def dailylog_set_level(self, level):
        """
        Sets the log level of the daily log handler

        @param level int: log level, see logging
        """
        self._daily_loghandler.setLevel(level)

    def save_data(self, data, filepath, parameters=None, filename=None,
                  filelabel=None, timestamp=None, as_text=True, as_xml=False,
                  precision=':.3e', delimiter='\t', plotfig=None):
        """ General save routine for data.

        @param dict or OrderedDict data:
                                  Any dictonary with a keyword of the data
                                  and a corresponding list, where the data
                                  are situated. E.g. like:

                     data = {'Frequency (MHz)':[1,2,4,5,6]}
                     data = {'Frequency':[1,2,4,5,6],'Counts':[234,894,743,423,235]}
                     data = {'Frequency (MHz),Counts':[ [1,234],[2,894],...[30,504] ]}

        @param string filepath: The path to the directory, where the data
                                  will be saved.
                                  If filepath is corrupt, the saving routine
                                  will retrieve the basic filepath for the
                                  data from the inherited base module
                                  'get_data_dir' and saves the data in the
                                  directory .../UNSPECIFIED_<module_name>/
        @param dict or OrderedDict parameters:
                                  optional, a dictionary
                                  with all parameters you want to pass to
                                  the saving routine.
        @parem string filename: optional, if you really want to fix an own
                                filename. BUT THIS IS NOT RECOMMENDED! If
                                passed the whole file will have the name

                                    <filename>

                                If nothing is specified the save logic will
                                generate a filename either based on the
                                class, from which this method was called,
                                or it will use the passed filelabel if that
                                is speficied.
                                Keep in mind that you have also to specify
                                the ending of the filename!
        @parem string filelabel: optional, if filelabel is set and no
                                 filename was specified, the savelogic will
                                 create a name which looks like

                                     YYYY-MM-DD_HHh-MMm-SSs_<filelabel>.dat

                                The timestamp will be created at runtime if
                                no user defined timestamp was passed.
        @param datetime timestamp: optional, a datetime.datetime object,
                                   which saves the timestamp in a general
                                   way. Create a datetime.datetime.now()
                                   object from the module datetime if you
                                   want to fix the timestamp for the
                                   filename. The filename will like in the
                                   description of the filelabel parameter.
                                   Be careful if you pass a filename and a
                                   timestamp, because then the timestamp
                                   will be not considered.
        @param bool as_text: specify how the saved data are saved to file.
        @param bool as_xml: specify how the saved data are saved to file.

        @param int precision: optional, specifies the number of digits
                              after the comma for the saving precision. All
                              number, which follows afterwards are cut off.
                              A c-like format should be used.
                              For 'precision=3' a number like
                                   '323.423842' is saved as '323.423'.
                                   Default is precision = 3.

        @param string delimiter: optional, insert here the delimiter, like
                                 \n for new line,  \t for tab, , for a
                                 comma, ect.

        This method should be called from the modules and it will call all
        the needed methods for the saving routine. This module guarentees
        that if the passing of the data is correct, the data are saved
        always.

        1D data
        =======
        1D data should be passed in a dictionary where the data trace
        should be assigned to one identifier like

            {'<identifier>':[list of values]}
            {'Numbers of counts':[1.4, 4.2, 5, 2.0, 5.9 , ... , 9.5, 6.4]}

        You can also pass as much 1D arrays as you want:
            {'Frequency (MHz)':list1, 'signal':list2, 'correlations': list3, ...}



        2D data
        =======
        2D data should be passed in a dictionary where the matrix like data
        should be assigned to one identifier like

            {'<identifier>':[[1,2,3],[4,5,6],[7,8,9]]}

        which will result in:
            <identifier>
            1   2   3
            4   5   6
            7   8   9

        3-X data
        ========
        There is no specific implementation to save 3D or higher dimension
        data arrays. If you split the N-dimensional data in N one
        dimensional data traces, which have a length of M (see last example
        in 1D data) then the savelogic will handle them. If the save logic
        cannot identify the passed data as 1D or 2D data, the data will be
        saved in a raw fashion.


        YOU ARE RESPONSIBLE FOR THE IDENTIFIER! DO NOT FORGET THE UNITS FOR THE
        SAVED TIME TRACE/MATRIX.
        """

        try:
            frm = inspect.stack()[1]    # try to trace back the functioncall to
                                        # the class which was calling it.
            mod = inspect.getmodule(frm[0])  # this will get the object, which
                                             # called the save_data function.
            module_name = mod.__name__.split('.')[-1]  # that will extract the
                                                       # name of the class.
        except:
            # Sometimes it is not possible to get the object which called the save_data function (such as when calling this from the console).
            module_name = 'NaN'

        # check whether the given directory path does exist. If not, the
        # file will be saved anyway in the unspecified directory.

        if not os.path.exists(filepath):
            filepath = self.get_daily_directory('UNSPECIFIED_' + str(module_name))
            self.log.warning('No Module name specified! Please correct this! '
                    'Data are saved in the \'UNSPECIFIED_<module_name>\' '
                    'folder.')

        # Produce a filename tag from the active POI name
        if self.active_poi_name == '':
            poi_tag = ''
        else:
            poi_tag = '_' + self.active_poi_name.replace(" ", "_")

        # create a unique name for the file, if no name was passed:
        if filename is None:
            # use the timestamp if that is specified:
            if timestamp is not None:
                # use the filelabel if that is specified:
                if filelabel is None:
                    filename = timestamp.strftime('%Y%m%d-%H%M-%S' + poi_tag + '_' + module_name + '.dat')
                else:
                    filename = timestamp.strftime('%Y%m%d-%H%M-%S' + poi_tag + '_' + filelabel + '.dat')
            else:
                # use the filelabel if that is specified:
                if filelabel is None:
                    filename = time.strftime('%Y%m%d-%H%M-%S' + poi_tag + '_' + module_name + '.dat')
                else:
                    filename = time.strftime('%Y%m%d-%H%M-%S' + poi_tag + '_' + filelabel + '.dat')

        # open the file
        textfile = open(os.path.join(filepath, filename), 'w')

        # write the paramters if specified:
        textfile.write(
            '# Saved Data from the class {0} on {1}.\n'
            ''.format(module_name, time.strftime('%d.%m.%Y at %Hh%Mm%Ss')))
        textfile.write('#\n')
        textfile.write('# Parameters:\n')
        textfile.write('# ===========\n')
        textfile.write('#\n')

        # Include the active POI name (if not empty) as a parameter in the header
        if self.active_poi_name != '':
            textfile.write('# Measured at POI: {0}\n'.format(self.active_poi_name))

        if parameters is not None:

            # check whether the format for the parameters have a dict type:
            if type(parameters) is dict or OrderedDict:
                for entry, param in parameters.items():
                    if isinstance(param, float):
                        textfile.write(('# {0}:{1}{2' + precision + '}\n').format(entry, delimiter, param))
                    else:
                        textfile.write('# {0}:{1}{2}\n'.format(entry, delimiter, param))

            # make a hardcore string convertion and try to save the
            # parameters directly:
            else:
                self.log.error(
                    'The parameters are not passed as a dictionary! '
                    'The SaveLogic will try to save the parameters directly.')
                textfile.write('# not specified parameters: {0}\n'.format(parameters))

        textfile.write('#\n')
        textfile.write('# Data:\n')
        textfile.write('# =====\n')
        # check the input data:

        # go through each data in t
        if len(data) == 1:
            key_name = list(data.keys())[0]

            # check whether the data is only a 1d trace
            if len(np.shape(data[key_name])) == 1:

                self.save_1d_trace_as_text(trace_data=data[key_name],
                                           trace_name=key_name,
                                           opened_file=textfile,
                                           precision=precision)

            # check whether the data is only a 2d array
            elif len(np.shape(data[key_name])) == 2:

                key_name_array = key_name.split(',')

                self.save_2d_points_as_text(trace_data=data[key_name],
                                            trace_name=key_name_array,
                                            opened_file=textfile,
                                            precision=precision,
                                            delimiter=delimiter)
            elif len(np.shape(data[key_name])) == 3:

                self.log.warning('Savelogic has no implementation for 3 '
                        'dimensional arrays. The data is saved in a '
                        'raw fashion.')
                textfile.write(str(data[key_name]))

            else:

                self.log.warning('Savelogic has no implementation for 4 '
                        'dimensional arrays. The data is saved in a '
                        'raw fashion.')
                textfile.write(+str(data[key_name]))

        else:
            key_list = list(data)

            trace_1d_flag = True

            data_traces = []
            for entry in key_list:
                data_traces.append(data[entry])
                if len(np.shape(data[entry])) > 1:
                    trace_1d_flag = False

            if trace_1d_flag:

                self.save_N_1d_traces_as_text(trace_data=data_traces,
                                              trace_name=key_list,
                                              opened_file=textfile,
                                              precision=precision,
                                              delimiter=delimiter)
            else:
                # go through each passed element again and treat them as
                # independant, i.e. each element is saved in an extra file.
                # That is an recursive procedure:

                for entry in key_list:
                    self.save_data(data={entry: data[entry]},
                                   filepath=filepath,
                                   parameters=parameters,
                                   filename=filename[:-4] + '_' + entry + '.dat',
                                   as_text=True, as_xml=False,
                                   precision=precision, delimiter=delimiter)

        textfile.close()

        # Save thumbnail figure of plot
        if plotfig is not None:
            fig_fname_image = os.path.join(filepath, filename)[:-4] + '_fig.png'
            fig_fname_vector = os.path.join(filepath, filename)[:-4] + '_fig.pdf'
            plotfig.savefig(fig_fname_image, bbox_inches='tight', pad_inches=0.05)
            plotfig.savefig(fig_fname_vector, bbox_inches='tight', pad_inches=0.05)

    def save_1d_trace_as_text(self, trace_data, trace_name, opened_file=None,
                              filepath=None, filename=None, precision=':.3f'):
        """An Independent method, which can save a 1d trace.

        If you call this method but you are respondible, that the passed
        optional parameters are correct."""

        close_file_flag = False

        if opened_file is None:
            opened_file = open(os.path.join(filepath, filename + '.dat'), 'wb')
            close_file_flag = True

        opened_file.write('# ' + str(trace_name) + '\n')

        for entry in trace_data:
            # If entry is a string, then print directly
            if isinstance(entry, str):
                opened_file.write(entry + '\n')
            # Otherwise, format number to requested precision
            else:
                opened_file.write(str('{0' + precision + '}\n').format(entry))

        if close_file_flag:
            opened_file.close()

    def save_N_1d_traces_as_text(self, trace_data, trace_name, opened_file=None,
                                 filepath=None, filename=None, precision=':.3f',
                                 delimiter='\t'):
        """An Independent method, which can save a N 1d trace.

        If you call this method but you are respondible, that the passed
        optional parameters are correct."""

        close_file_flag = False

        if opened_file is None:
            opened_file = open(os.path.join(filepath, filename + '.dat'), 'wb')
            close_file_flag = True

        if trace_name is not None:
            opened_file.write('# ')
            for name in trace_name:
                opened_file.write(name + delimiter)
            opened_file.write('\n')

        max_trace_length = max(np.shape(trace_data))

        for row in range(max_trace_length):
            for column in trace_data:
                try:
                    # TODO: Lachlan has inserted the if-else in here,
                    # but it should be properly integrated with the try

                    # If entry is a string, then print directly
                    if isinstance(column[row], str):
                        opened_file.write(str('{0}' + delimiter).format(column[row]))
                    # Otherwise, format number to requested precision
                    else:
                        opened_file.write(str('{0' + precision + '}' + delimiter).format(column[row]))
                except:
                    opened_file.write(str('{0}' + delimiter).format('NaN'))
            opened_file.write('\n')

        if close_file_flag:
            opened_file.close()

    def save_2d_points_as_text(self, trace_data, trace_name=None, opened_file=None,
                               filepath=None, filename=None, precision=':.3f',
                               delimiter='\t'):
        """An Independent method, which can save a matrix like array to file.

        If you call this method but you are respondible, that the passed
        optional parameters are correct."""

        close_file_flag = False

        if opened_file is None:
            opened_file = open(os.path.join(filepath, filename + '.dat'), 'wb')
            close_file_flag = True

        # write the trace names:
        if trace_name is not None:
            opened_file.write('# ')
            for name in trace_name:
                opened_file.write(name + delimiter)
            opened_file.write('\n')

        for row in trace_data:
            for entry in row:
                if units.is_number(entry):
                    opened_file.write(str('{0' + precision + '}' + delimiter).format(entry))
                else:
                    opened_file.write(str(entry).encode('utf-8'))
            opened_file.write('\n')

        if close_file_flag:
            opened_file.close()

    def _save_1d_traces_as_xml(self):
        """ Save 1d data trace in xml conding. """
        pass
#        if as_xml:
#
#            root = ET.Element(module_name)  # which class wanted to access the save
#                                            # function
#
#            para = ET.SubElement(root, 'Parameters')
#
#            if parameters != None:
#                for element in parameters:
#                    ET.SubElement(para, element).text = parameters[element]
#
#            data_xml = ET.SubElement(root, 'data')
#
#            for entry in data:
#
#                dimension_data_array = len(np.shape(data[entry]))
#
#                # filter out the events which has only a single trace:
#                if dimension_data_array == 1:
#
#                    value = ET.SubElement(data_xml, entry)
#
#                    for list_element in data[entry]:
#
#                        ET.SubElement(value, 'value').text = str(list_element)
#
#                elif dimension_data_array == 2:
#
#                    dim_list_entry = len(np.shape(data[entry][0]))
#                    length_list_entry = np.shape(data[entry][0])[0]
#                    if (dim_list_entry == 1) and (np.shape(data[entry][0])[0] == 2):
#
#                        # get from the keyword, which should be within the string
#                        # separated by the delimiter ',' the description for the
#                        # values:
#                        try:
#                            axis1 = entry.split(',')[0]
#                            axis2 = entry.split(',')[1]
#                        except:
#                            print('Enter a commaseparated description for the given values!!!')
#                            print('like:  dict_data[\'Frequency (MHz), Signal (arb. u.)\'] = 2d_list ')
#                            print('But your data will be saved.')
#
#                            axis1 = str(entry)
#                            axis2 = 'value2'
#
#                        for list_element in data[entry]:
#
#                            element = ET.SubElement(data_xml, 'value' ).text = str(list_element)
##
##                            ET.SubElement(element, str(axis1)).text = str(list_element[0])
##                            ET.SubElement(element, str(axis2)).text = str(list_element[1])
#
#                    elif (dim_list_entry == 1):
#
#                        for list_element in data[entry]:
#
#                            row = ET.SubElement(data_xml, 'row')
#
#                            for sub_element in list_element:
#
#                                ET.SubElement(row, 'value').text = str(sub_element)
#
#
#
#            #write to file:
#            tree = ET.ElementTree(root)
#            tree.write('output.xml', pretty_print=True, xml_declaration=True)

    def _save_2d_data_as_xml(self):
        """ Save 2d data in xml conding."""
        pass

    def get_daily_directory(self):
        """
        Creates the daily directory.

          @return string: path to the daily directory.

        If the daily directory does not exits in the specified <root_dir> path
        in the config file, then it is created according to the following scheme:

            <root_dir>\<year>\<month>\<yearmonthday>

        and the filepath is returned. There should be always a filepath
        returned.
        """

        # First check if the directory exists and if not then the default
        # directory is taken.
        if not os.path.exists(self.data_dir):
                if self.data_dir != '':
                    self.log.warning('The specified Data Directory in the '
                            'config file does not exist. Using default '
                            'instead.')
                if self.os_system == 'unix':
                    self.data_dir = self.default_unix_data_dir
                elif self.os_system == 'win':
                    self.data_dir = self.default_win_data_dir
                else:
                    self.log.error('Identify the operating system.')

                # Check if the default directory does exist. If yes, there is
                # no need to create it, since it will overwrite the existing
                # data there.
                if not os.path.exists(self.data_dir):
                    os.makedirs(self.data_dir)
                    self.log.warning('The specified Data Directory in the '
                            'config file does not exist. Using default for '
                            '{0} system instead. The directory {1} was '
                            'created'.format(self.os_system, self.data_dir))

        # That is now the current directory:
        current_dir = os.path.join(self.data_dir, time.strftime("%Y"), time.strftime("%m"))

        folder_exists = False   # Flag to indicate that the folder does not exist.
        if os.path.exists(current_dir):

            # Get only the folders without the files there:
            folderlist = [d for d in os.listdir(current_dir) if os.path.isdir(os.path.join(current_dir, d))]
            # Search if there is a folder which starts with the current date:
            for entry in folderlist:
                if (time.strftime("%Y%m%d") in (entry[:2])):
                    current_dir = os.path.join(current_dir, str(entry))
                    folder_exists = True
                    break

        if not folder_exists:
            current_dir = os.path.join(current_dir, time.strftime("%Y%m%d"))
            self.log.info('Creating directory for today\'s data in \n'
                    '{0}'.format(current_dir))

            # The exist_ok=True is necessary here to prevent Error 17 "File Exists"
            # Details at http://stackoverflow.com/questions/12468022/python-fileexists-error-when-making-directory
            os.makedirs(current_dir, exist_ok=True)

        return current_dir

    def get_path_for_module(self, module_name=None):
        """
        Method that creates a path for 'module_name' where data are stored.

          @param string module_name: Specify the folder, which should be
                                     created in the daily directory. The
                                     module_name can be e.g. 'Confocal'.
          @retun string: absolute path to the module name

        This method should be called directly in the saving routine and NOT in
        the init method of the specified module! This prevents to create empty
        folders!

        """
        if module_name is None:
            self.log.warning('No Module name specified! Please correct this! '
                    'Data is saved in the \'UNSPECIFIED_<module_name>\' '
                    'folder.')

            frm = inspect.stack()[1]    # try to trace back the functioncall to
                                        # the class which was calling it.
            mod = inspect.getmodule(frm[0]) # this will get the object, which
                                            # called the save_data function.
            module_name =  mod.__name__.split('.')[-1]  # that will extract the
                                                        # name of the class.
            module_name = 'UNSPECIFIED_' + module_name

        dir_path = os.path.join(self.get_daily_directory(), module_name)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        return dir_path
