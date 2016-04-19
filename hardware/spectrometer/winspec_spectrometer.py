# -*- coding: utf-8 -*-
"""
Acquire a spectrum using Winspec through the COM interface.
This program gets the data from WinSpec, saves them and
gets the data for plotting.

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

Derived from the pyPL project (https://github.com/kaseyrussell/pyPL)
Copyright 2010 Kasey Russell ( email: krussell _at_ post.harvard.edu )

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""

from core.base import Base
from interface.spectrometer_interface import SpectrometerInterface
from collections import OrderedDict
from core.util.mutex import Mutex

from pyqtgraph.Qt import QtCore

import numpy as np
import comtypes.client as ctc
import win32com.client as w32c
from win32com.client import constants
from ctypes import byref, pointer, c_long, c_float, c_bool
from time import strftime, localtime

import datetime

ctc.GetModule( ('{1A762221-D8BA-11CF-AFC2-508201C10000}', 3, 11) )
import comtypes.gen.WINX32Lib as WinSpecLib


class WinSpec32(Base, SpectrometerInterface):

    _out = {'spec': 'SpectrometerInterface'}

    def __init__(self, manager, name, configuration):
        cb = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self,manager,name,configuration, cb)

    def activation(self, e):
        w32c.pythoncom.CoInitialize()
        self.expt_is_running = WinSpecLib.EXP_RUNNING
        self.path = 'asdf'
        self.prefix = 'test'

    def deactivation(self, e):
        pass

    def recordSpectrum(self):
        w32c.pythoncom.CoInitialize()
        # get some data structures from COM that we need later
        self.WinspecDoc = w32c.Dispatch("WinX32.DocFile")
        self.WinspecDocs = w32c.Dispatch("WinX32.DocFiles")
        self.WinspecExpt = w32c.Dispatch("WinX32.ExpSetup")

        # Close all documents so we do not get any errors or prompts to save the currently opened spectrum in WinSpec32
        self.WinspecDocs.CloseAll()

        if self.WinspecExpt.Start(self.WinspecDoc)[0]:
            # start the experiment
            # Wait for acquisition to finish (and check for errors continually)
            # If we didn't care about errors, we could just run WinspecExpt.WaitForExperiment()
            self.expt_is_running, self.status = self.WinspecExpt.GetParam(WinSpecLib.EXP_RUNNING)

            while self.expt_is_running and self.status == 0:
                self.expt_is_running, self.status = self.WinspecExpt.GetParam(WinSpecLib.EXP_RUNNING)

            if self.status != 0:
                print('Error running experiment.')

            #timestr = strftime("_%Y-%m-%d_%H%M%S", localtime())
            #self.WinspecDoc.SetParam(
            #    WinSpecLib.DM_FILENAME,
            #    str(self.path) + str(self.prefix) + timestr + ".spe"
            #    )
            ##print(self.WinspecDoc.GetParam(WinSpecLib.DM_FILENAME))
            #self.WinspecDoc.Save()

            """
                Pass a pointer to Winspec so it can put the spectrum in a place in
                memory where python will be able to find it.
            """
            datapointer = c_float()
            raw_spectrum = self.WinspecDoc.GetFrame(1, datapointer)
            spectrum = np.array(raw_spectrum).flatten()
            specdata = np.empty((2, len(spectrum)), dtype=np.double)
            specdata[1] = spectrum
            calibration = self.WinspecDoc.GetCalibration()

            if calibration.Order != 2:
                raise ValueError('Cannot handle current WinSpec wavelength calibration.')
            """
                WinSpec doesn't actually store the wavelength information as an array but
                instead calculates it every time you plot using the calibration information
                stored with the spectrum.
            """
            p = np.array([
                    calibration.PolyCoeffs(2),
                    calibration.PolyCoeffs(1),
                    calibration.PolyCoeffs(0)
                ])
            specdata[0] = np.polyval(p, range(1, 1+len(spectrum)))
            return specdata

        else:
            print("Could not initiate acquisition.")
            return {'wavelength': [0], 'intensity': [0]}

    def saveSpectrum(self, path, postfix = ''):
        savetime=datetime.datetime.now()
        w32c.pythoncom.CoInitialize()
        timestr = savetime.strftime("%Y%m%d-%H%M-%S-%f_")
        self.WinspecDoc.SetParam(
            WinSpecLib.DM_FILENAME,
            str(path) + timestr + str(postfix) + ".spe"
        )
        print(self.WinspecDoc.GetParam(WinSpecLib.DM_FILENAME))
        self.WinspecDoc.Save()

    def getExposure(self):
        return -1

    def setExposure(self, exposureTime):
        pass
