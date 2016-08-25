# -*- coding: utf-8 -*-
"""
This is a module for using a spectrometer through the Princeton Instruments
Lightfield software.

This module is still unusable and fucking broken and very probably
just crashes Lightfield.

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

from core.base import Base
from interface.spectrometer_interface import SpectrometerInterface

import os
import sys
from enum import Enum

# .Net imports
import clr
import System
from System import EventHandler, EventArgs
import System.Collections.Generic as col


class LFImageMode(Enum):
    LFImageModeNormal = 1
    LFImageModePreview = 2
    LFImageModeBackground = 3


class Lightfield(Base, SpectrometerInterface):

    _out = {'spec': 'SpectrometerInterface'}

    def on_activate(self, e):

        lfpath = os.environ['LIGHTFIELD_ROOT']
        lfaddinpath = os.path.join(os.environ['LIGHTFIELD_ROOT'], 'AddInViews')

        sys.path.append(lfpath)
        sys.path.append(lfaddinpath)
        ref1 = clr.AddReference('PrincetonInstruments.LightFieldViewV4')
        ref2 = clr.AddReference('PrincetonInstruments.LightField.AutomationV4')
        #print(dir(ref), '\n\n')
        #ref.LoadFrom(ref.Location)

        verbose = list(clr.ListAssemblies(True))
        short = list(clr.ListAssemblies(False))
        #for i in short:
        #        print('ASSEMBLY:', i)
        #for i in verbose:
        #    print('ASS:', i)

        #for i in ref2.Modules:
        #    print('ASS Module:', i)
        #for i in ref2.ExportedTypes:
        #    print('ASS Exported type:', i)
        try:
            for i in ref2.DefinedTypes:
                print('ASS Defined type:', i)
        except System.Reflection.ReflectionTypeLoadException as e:
            for i in e.LoaderExceptions:
                print('EXC:', i.Message)

        print('ASS Entry point:', ref2.EntryPoint)
        print('ASS is Dynamic:', ref2.IsDynamic)

        from PrincetonInstruments.LightField.Automation import Automation
        import PrincetonInstruments.LightField.AddIns as ai

        lst = col.List[System.String]()
        self.au = Automation(True, lst)
        self.app = self.au.LightFieldApplication
        self.exp = self.app.Experiment

        self.exp.ExperimentCompleted += EventHandler(self.setAcquisitionComplete)
        self.exp.ImageDataSetReceived += EventHandler(self.frameCallback)
        self.exp.SettingChanged += EventHandler(self.settingChangedCallback)

        self.app.UserInteractionManager.SuppressUserInteraction = True

        self.prevExperimentName = self.exp.Name
        print('Prev Exp', self.prevExperimentName)
        #self.getExperimentList()
        #self.openExperiment(name)
        self.lastframe = list()

    def on_deactivate(self, e):
        if hasattr(self, 'au'):
            del self.au

# Callbacks
    def settingChangedCallback(self, sender, args):
        pass

    def exitHandler(self, sender, args):
        del self.au

    def frameCallback(self, sender, args):
        print(sender)
        print(args)
        dataSet = args.ImageDataSet
        frame = dataSet.GetFrame(0, 0)
        arr = frame.GetData()
        print(arr)
        print(arr[0])
        print(frame.Format)

        dims = [frame.Width, frame.Height]
        print(dims)
        self.lastframe = list(arr)

    def setAcquisitionComplete(self, sender, args):
        pass

# other stuff
    def getExperimentList(self):
        pass

    def openExperiment(self, expName):
        pass

    def buildFeatureList(self, feature):
        pass

    def startAcquire(self):
        self.calibration = self.exp.SystemColumnCalibration
        self.calerrors = self.exp.SystemColumnCalibrationErrors
        self.intcal = self.exp.SystemIntensityCalibration
        if self.exp.IsReadyToRun:
            self.exp.Acquire()

    def setFilePathAndName(self, autoIncrement):
        pass

    def setBackgroundFile(self):
        pass

    def getROI(self):
        pass

    def setROI(self):
        pass

    def setShutter(self, isOpen):
        pass

    def recordSpectrum(self):
        pass
