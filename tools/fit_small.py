# -*- coding: utf-8 -*-
"""
This file contains the QuDi FitLogic class, which provides all
fitting methods imported from the files in logic/fitmethods.

The fit_logic methods can be imported in any python code by using
the folling lines:

import sys
path_of_qudi = "<custom path>/qudi/"
sys.path.append(path_of_qudi)
from tools.fit_logic_standalone import FitLogic
fitting = FitLogic(path_of_qudi)



QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


import logging
logger = logging.getLogger(__name__)

import importlib
import sys
import os


class FitLogic():
        """
        This file contains a test bed for implementation of new fit
        functions and estimators. Here one can also do stability checks
        with dummy data.

        All methods in the folder logic/fitmethods/ are imported here.

        This is a playground so no conventions have to be
        taken into account. This is completely standalone and does not interact
        with qudi. It only will import the fitting methods from qudi.

        """
        def __init__(self, path_of_qudi=None):

            self.log = logger
            
            filenames = []
            self.mods = []

            if path_of_qudi is None:
                # get from this script the absolte filepath:
                file_path = os.path.realpath(__file__)

                # retrieve the path to the directory of the file:
                script_dir_path = os.path.dirname(file_path)

                # retrieve the path to the directory of the qudi module:
                mod_path = os.path.dirname(script_dir_path)

            else:
                mod_path = path_of_qudi

            fitmodules_path = os.path.join(mod_path, 'logic', 'fitmethods')

            if fitmodules_path not in sys.path:
                sys.path.append(fitmodules_path)

            for f in os.listdir(fitmodules_path):
                if os.path.isfile(os.path.join(fitmodules_path, f)) and f.endswith(".py"):
                    filenames.append(f[:-3])

            oneD_fit_methods = dict()
            twoD_fit_methods = dict()

            for files in filenames:
                mod = importlib.import_module('{0}'.format(files))
                self.mods.append(mod)
                
                for method in dir(mod):
                    try:
                        if callable(getattr(mod, method)):

                            # import methods in Fitlogic
                            setattr(FitLogic, method, getattr(mod, method))

                            # add method to dictionary and define what
                            # estimators they have

                            # check if it is a make_<own fuction>_fit method

                            if (str(method).startswith('make_')
                                and str(method).endswith('_fit')):

                                # only add to dictionary if it is not already there
                                if 'twoD' in str(method) and str(method).split('_')[1] not in twoD_fit_methods:
                                    twoD_fit_methods[str(method).split('_')[1]] = []
                                    
                                elif str(method).split('_')[1] not in oneD_fit_methods:
                                    oneD_fit_methods[str(method)[5:-4]] = []
                                    
                            # if there is an estimator add it to the dictionary
                            if 'estimate' in str(method):
                                if 'twoD' in str(method):
                                    
                                    try: # if there is a given estimator it will be set or added
                                        if str(method).split('_')[1] in twoD_fit_methods:
                                            twoD_fit_methods[str(method).split('_')[1]] = twoD_fit_methods[str(method).split('_')[1]].append(str(method).split('_')[2])
                                        else:
                                            twoD_fit_methods[str(method).split('_')[1]] = [str(method).split('_')[2]]
                                    except:  # if there is no estimator but only a standard one the estimator is empty
                                        if not str(method).split('_')[1] in twoD_fit_methods:
                                            twoD_fit_methods[str(method).split('_')[1]] = []
                                            
                                else: # this is oneD case
                                    try: # if there is a given estimator it will be set or added
                                        
                                        if (str(method).split('_')[1] in oneD_fit_methods and str(method).split('_')[2] is not None):
                                            oneD_fit_methods[str(method).split('_')[1]].append(str(method).split('_')[2])
                                        elif str(method).split('_')[2] is not None:
                                            oneD_fit_methods[str(method).split('_')[1]]=[str(method).split('_')[2]]
                                            
                                    except: # if there is no estimator but only a standard one the estimator is empty
                                        if not str(method).split('_')[1] in oneD_fit_methods:
                                            oneD_fit_methods[str(method).split('_')[1]]=[]
                    except:
                        self.log.error('It was not possible to import element {} into FitLogic.'.format(method))
                        
            self.log.info('Methods were included to FitLogic, but only if naming is right: '
                          'make_<own method>_fit. If estimator should be added, the name has')
            
        def reload(self):
            modsref = self.mods
            self.mods = []
            for mod in modsref:
                print(mod)
                self.mods.append(importlib.reload(mod))
                
