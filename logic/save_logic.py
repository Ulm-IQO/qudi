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
import datetime
import numpy as np

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.util import units
# Use the PDF backend to attach metadata
from matplotlib.backends.backend_pdf import PdfPages
# Use Pillow (active fork from PIL) to attach metadata to PNG files
from PIL import Image
from PIL import PngImagePlugin

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

    def save_data(self, data, filepath=None, parameters=None, filename=None, filelabel=None,
                  timestamp=None, filetype='text', fmt='%.15e', delimiter='\t', plotfig=None):
        """
        General save routine for data.

        @param dictionary data: Dictionary containing the data to be saved. The keys should be
                                strings containing the data header/description. The corresponding
                                items are 1D or 2D arrays containing the data (list or
                                numpy.ndarray). Example:

                                    data = {'Frequency (MHz)': [1,2,4,5,6]}
                                    data = {'Frequency': [1, 2, 4], 'Counts': [234, 894, 743, 423]}
                                    data = {'Frequency (MHz),Counts':[[1,234], [2,894],...[30,504]]}

        @param string filepath: optional, the path to the directory, where the data will be saved.
                                If the specified path does not exist yet, the saving routine will
                                try to create it.
                                If no path is passed (default filepath=None) the saving routine will
                                create a directory by the name of the calling module inside the
                                daily data directory.
                                If no calling module can be inferred and/or the requested path can
                                not be created the data will be saved in a subfolder of the daily
                                data directory called UNSPECIFIED
        @param dictionary parameters: optional, a dictionary with all parameters you want to save in
                                      the header of the created file.
        @parem string filename: optional, if you really want to fix your own filename. If passed,
                                the whole file will have the name

                                    <filename>

                                If nothing is specified the save logic will generate a filename
                                either based on the module name from which this method was called,
                                or it will use the passed filelabel if that is speficied.
                                You also need to specify the ending of the filename!
        @parem string filelabel: optional, if filelabel is set and no filename was specified, the
                                 savelogic will create a name which looks like

                                     YYYY-MM-DD_HHh-MMm-SSs_<filelabel>.dat

                                 The timestamp will be created at runtime if no user defined
                                 timestamp was passed.
        @param datetime timestamp: optional, a datetime.datetime object. You can create this object
                                   with datetime.datetime.now() in the calling module if you want to
                                   fix the timestamp for the filename. Be careful when passing a
                                   filename and a timestamp, because then the timestamp will be
                                   ignored.
        @param string filetype: optional, the file format the data should be saved in. Valid inputs
                                are 'text', 'xml' and 'npz'. Default is 'text'.
        @param string fmt: optional, format specifier for saved data. See python documentation
                              for "Format Specification Mini-Language". If you want for example save
                              a float in scientific notation with 6 decimals this would look like
                              '%.6e'. For saving integers you could use '%d', '%s' for strings.
                              The default is '%.15e'.
        @param string delimiter: optional, insert here the delimiter, like '\n' for new line, '\t'
                                 for tab, ',' for a comma ect.

        1D data
        =======
        1D data should be passed in a dictionary where the data trace should be assigned to one
        identifier like

            {'<identifier>':[list of values]}
            {'Numbers of counts':[1.4, 4.2, 5, 2.0, 5.9 , ... , 9.5, 6.4]}

        You can also pass as much 1D arrays as you want:

            {'Frequency (MHz)':list1, 'signal':list2, 'correlations': list3, ...}

        2D data
        =======
        2D data should be passed in a dictionary where the matrix like data should be assigned to
        one identifier like

            {'<identifier>':[[1,2,3],[4,5,6],[7,8,9]]}

        which will result in:
            <identifier>
            1   2   3
            4   5   6
            7   8   9

        3D-ND data
        ========
        There is no generic style to save 3D or higher dimension data arrays. If you split the
        N-dimensional data in N one dimensional data traces by flattening them for example, the
        savelogic will handle them. If you are still trying to pass multidimensional (N>2) data, it
        will get saved as a binary numpy .npz-file.

        YOU ARE RESPONSIBLE FOR THE IDENTIFIER! DO NOT FORGET THE UNITS FOR THE
        SAVED TIME TRACE/MATRIX.
        """
        # Create timestamp if none is present
        if timestamp is None:
            timestamp = datetime.datetime.now()

        # Try to cast data array into numpy.ndarray if it is not already one
        for keyname in data:
            if not isinstance(data[keyname], np.ndarray):
                try:
                    data[keyname] = np.array(data[keyname])
                except:
                    self.log.error('Casting data array of type "{0}" into numpy.ndarray failed. '
                                   'Could not save data.'.format(type(data[keyname])))
                    return -1

        # try to trace back the functioncall to the class which was calling it.
        try:
            frm = inspect.stack()[1]
            # this will get the object, which called the save_data function.
            mod = inspect.getmodule(frm[0])
            # that will extract the name of the class.
            module_name = mod.__name__.split('.')[-1]
        except:
            # Sometimes it is not possible to get the object which called the save_data function
            # (such as when calling this from the console).
            module_name = 'UNSPECIFIED'

        # determine proper file path
        if filepath is None:
            filepath = self.get_path_for_module(module_name)
        elif not os.path.exists(filepath):
            os.makedirs(filepath)
            self.log.info('Custom filepath does not exist. Created directory "{0}"'
                          ''.format(filepath))

        # create filelabel if none has been passed
        if filelabel is None:
            filelabel = module_name
        if self.active_poi_name != '':
            filelabel = self.active_poi_name.replace(' ', '_') + '_' + filelabel

        # determine proper unique filename to save if none has been passed
        if filename is None:
            filename = timestamp.strftime('%Y%m%d-%H%M-%S' + '_' + filelabel + '.dat')

        # Create header string for the file
        header = 'Saved Data from the class {0} on {1}.\n' \
                 ''.format(module_name, timestamp.strftime('%d.%m.%Y at %Hh%Mm%Ss'))
        header += '\nParameters:\n===========\n\n'
        # Include the active POI name (if not empty) as a parameter in the header
        if self.active_poi_name != '':
            header += 'Measured at POI: {0}\n'.format(self.active_poi_name)
        # add the parameters if specified:
        if parameters is not None:
            # check whether the format for the parameters have a dict type:
            if isinstance(parameters, dict):
                for entry, param in parameters.items():
                    if isinstance(param, float):
                        header += '{0}: {1:.16e}\n'.format(entry, param)
                    else:
                        header += '{0}: {1}\n'.format(entry, param)
            # make a hardcore string conversion and try to save the parameters directly:
            else:
                self.log.error('The parameters are not passed as a dictionary! The SaveLogic will '
                               'try to save the parameters nevertheless.')
                header += 'not specified parameters: {0}\n'.format(parameters)
        header += '\nData:\n=====\n'

        # Reorganise data arrays if necessary and save them. Also check if arrays have equal length.
        found_1d = False
        found_2d = False
        found_xd = False
        unequal_length = False
        for keyname in data:
            if data[keyname].ndim == 1:
                found_1d = True
            elif data[keyname].ndim == 2:
                found_2d = True
            elif data[keyname].ndim > 2:
                found_xd = True
        if found_xd:
            if filetype != 'npz':
                self.log.error('Passed multidimensional (N>2) array(s). These can only be saved in '
                               'binary .npz format. Filetype ignored.')
            data['header'] = np.array(header)
            np.savez(os.path.join(filepath, filename), **data)
        elif found_1d and found_2d:
            self.log.warning('Passed mixture of 1D and 2D arrays. Morph 2D into 1D arrays.')

        # write data to file
        if len(data) == 1:
            # if data is a single array just write it to file
            key_name = list(data)[0]

            if data[key_name].ndim > 1:
                for name in key_name.split(','):
                    header = header + name + delimiter
            else:
                header = header + key_name

            if data[key_name].ndim < 3:
                self.save_array_as_text(data=data[key_name], filename=filename, filepath=filepath,
                                        precision=precision, header=header, delimiter=delimiter,
                                        append=False)
            else:
                self.log.warning('Savelogic has no implementation for 3 dimensional arrays. The '
                                 'data is saved in a raw fashion.')
                with open(os.path.join(filepath, filename), 'w') as file:
                    file.write(str(data[key_name]))
        else:
            # If more data arrays have been passed check if each one is a 1D array.
            # Save to file if that is the case. If multidimensional arrays are present,
            # recursively call this method again for each array. This will lead to multiple
            # individual files.
            key_list = list(data)

            array_1d_flag = True

            data_traces = []
            for entry in key_list:
                data_traces.append(data[entry])
                if data[entry].ndim > 1:
                    trace_1d_flag = False

            if array_1d_flag:
                for entry in key_list:
                    header = header + entry + delimiter

                self.save_array_as_text(data=np.transpose(np.array(data_traces)), filename=filename,
                                        filepath=filepath, precision=precision, header=header,
                                        delimiter=delimiter, append=False)
            else:
                for entry in key_list:
                    self.save_data(data={entry: data[entry]},
                                   filepath=filepath,
                                   parameters=parameters,
                                   filename=filename[:-4] + '_' + entry + '.dat',
                                   as_text=True, as_xml=False,
                                   precision=precision, delimiter=delimiter)

        #--------------------------------------------------------------------------------------------
        # Save thumbnail figure of plot
        if plotfig is not None:
            # create Metadata
            metadata = dict()
            metadata['Title'] = 'Image produced by qudi: ' + module_name
            metadata['Author'] = 'qudi - Software Suite'
            metadata['Subject'] = 'Find more information on: https://github.com/Ulm-IQO/qudi'
            metadata['Keywords'] = 'Python 3, Qt, experiment control, automation, measurement, software, framework, modular'
            metadata['Producer'] = 'qudi - Software Suite'
            if timestamp is not None:
                metadata['CreationDate'] = timestamp
                metadata['ModDate'] = timestamp
            else:
                metadata['CreationDate'] = time
                metadata['ModDate'] = time

            # determine the PDF-Filename
            fig_fname_vector = os.path.join(filepath, filename)[:-4] + '_fig.pdf'

            # Create the PdfPages object to which we will save the pages:
            # The with statement makes sure that the PdfPages object is closed properly at
            # the end of the block, even if an Exception occurs.
            with PdfPages(fig_fname_vector) as pdf:
                pdf.savefig(plotfig, bbox_inches='tight', pad_inches=0.05)

                # We can also set the file's metadata via the PdfPages object:
                pdf_metadata = pdf.infodict()
                for x in metadata:
                    pdf_metadata[x] = metadata[x]

            # determine the PNG-Filename and save the plain PNG
            fig_fname_image = os.path.join(filepath, filename)[:-4] + '_fig.png'
            plotfig.savefig(fig_fname_image, bbox_inches='tight', pad_inches=0.05)

            # Use Pillow (an fork for PIL) to attach metadata to the PNG
            png_image = Image.open(fig_fname_image)
            png_metadata = PngImagePlugin.PngInfo()

            # PIL can only handle Strings, so let's convert our times
            metadata['CreationDate'] = metadata['CreationDate'].strftime('%Y%m%d-%H%M-%S')
            metadata['ModDate'] = metadata['ModDate'].strftime('%Y%m%d-%H%M-%S')

            for x in metadata:
                # make sure every value of the metadata is a string
                if not isinstance(metadata[x], str):
                    metadata[x] = str(metadata[x])

                # add the metadata to the picture
                png_metadata.add_text(x, metadata[x])

            # save the picture again, this time including the metadata
            png_image.save(fig_fname_image, "png", pnginfo=png_metadata)
            #----------------------------------------------------------------------------------


    def save_array_as_text(self, data, filename, filepath=None, precision='%.3f', header='',
                           delimiter='\t', append=False):
        """
        An Independent method, which can save a 1D or 2D data array.

        If you call this method but you are responsible, that the passed optional parameters are
        correct.
        """
        if data.ndim == 1:
            delimiter = '\n'

        # Add file extension ".dat" if not already present
        if not filename.endswith('.dat'):
            if '.' in filename:
                filename = filename.rsplit('.', 1)[0]
            filename = filename + '.dat'

        # turn precision specifier into a proper format specifier
        if precision.startswith(':'):
            precision = precision.replace(':', '%')

        # Check for string array and match precision specifier if necessary
        if data.dtype.type == np.bytes_ or data.dtype.type == np.str_:
            if 's' not in precision and 'S' not in precision:
                precision = '%s'
                self.log.warning('Tried to write string array to file but precision was '
                                 'corresponding to a number format. Changed it to "%s".')

        # write to file. Append if requested.
        if append:
            with open(os.path.join(filepath, filename), 'ab') as file:
                np.savetxt(file, data, fmt=precision, delimiter=delimiter, header=header,
                           comments='#')
        else:
            with open(os.path.join(filepath, filename), 'wb') as file:
                np.savetxt(file, data, fmt=precision, delimiter=delimiter, header=header,
                           comments='#')
        return

    def _save_array_as_xml(self):
        """ Save data in xml conding. """
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

    def get_path_for_module(self, module_name):
        """
        Method that creates a path for 'module_name' where data are stored.

        @param string module_name: Specify the folder, which should be created in the daily
                                   directory. The module_name can be e.g. 'Confocal'.
        @return string: absolute path to the module name
        """
        dir_path = os.path.join(self.get_daily_directory(), module_name)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        return dir_path
