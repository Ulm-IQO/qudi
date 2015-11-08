# -*- coding: utf-8 -*-
"""
    Acquire a spectrum using Winspec through the COM interface.
    This program gets the data from WinSpec, saves them and
    gets the data for plotting.

    Check the license for this again...
"""

from core.base import Base
from hardware.spectrometer.spectrometer_interface import SpectrometerInterface

import os
import sys
import time
import clr
import System
from System import EventHandler, EventArgs
import System.Collections.Generic as col


class Lightfield(Base, SpectrometerInterface):

    _out = {'spec': 'SpectrometerInterface'}

    def __init__(self, manager, name, configuration):
        cb = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self,manager,name,configuration, cb)

    def activation(self, e):

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

    def deactivation(self, e):
        if hasattr(self, 'au'):
            del self.au

# Callbacks
    def settingChangedCallback(self, sender, args):
        pass

    def exitHandler(self, sender, args):
        del self.au

    def frameCallback(self, sender, args):
        pass

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
        pass

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

