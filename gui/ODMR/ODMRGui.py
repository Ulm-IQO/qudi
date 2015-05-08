# -*- coding: utf-8 -*-
"""
Created on Fri May  8 11:28:26 2015

@author: user-admin
"""

#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

from collections import OrderedDict
from core.Base import Base
from gui.ODMR.ODMRGuiUI import Ui_MainWindow
from gui.ODMR.ODMRSettingsUI import Ui_SettingsDialog

# To convert the *.ui file to a raw ODMRGuiUI.py file use the python script
# in the Anaconda directory, which you can find in:
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py".
#
# Then use that script like
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py"ODMRGuiUI.ui > ODMRGuiUI.py


class ODMRMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        
class ODMRSettingDialog(QtGui.QDialog,Ui_SettingsDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)

            
               
            
class ODMRGui(Base,QtGui.QMainWindow,Ui_MainWindow):
    """
    This is the GUI Class for ODMR
    """
    
    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        
        self._modclass = 'ODMRGui'
        self._modtype = 'gui'
        
        ## declare connectors
        self.connector['in']['odmrlogic'] = OrderedDict()
        self.connector['in']['odmrlogic']['class'] = 'ODMRLogic'
        self.connector['in']['odmrlogic']['object'] = None
        self.connector['in']['savelogic'] = OrderedDict()
        self.connector['in']['savelogic']['class'] = 'SaveLogic'
        self.connector['in']['savelogic']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')  
                        
    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the ODMR GUI.
          
          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        
        """
        
        self._odmr_logic = self.connector['in']['odmrlogic']['object']
        print("ODMR logic is", self._optimiser_logic)
        
        self._save_logic = self.connector['in']['savelogic']['object']
        print("Save logic is", self._save_logic)  
        
        # Use the inherited class 'Ui_ODMRGuiUI' to create now the 
        # GUI element:
        self._mw = ODMRMainWindow()
        self._sd = ODMRSettingDialog()