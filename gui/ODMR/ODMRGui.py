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
#from gui.ODMR.ODMRSettingsUI import Ui_SettingsDialog

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
        
#class ODMRSettingDialog(QtGui.QDialog,Ui_SettingsDialog):
#    def __init__(self):
#        QtGui.QDialog.__init__(self)
#        self.setupUi(self)

            
               
            
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
        self.connector['in']['odmrlogic1'] = OrderedDict()
        self.connector['in']['odmrlogic1']['class'] = 'ODMRLogic'
        self.connector['in']['odmrlogic1']['object'] = None
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
        
        self._odmr_logic = self.connector['in']['odmrlogic1']['object']
        print("ODMR logic is", self._odmr_logic)
        
        self._save_logic = self.connector['in']['savelogic']['object']
        print("Save logic is", self._save_logic)  
        
        # Use the inherited class 'Ui_ODMRGuiUI' to create now the 
        # GUI element:
        self._mw = ODMRMainWindow()
#        self._sd = ODMRSettingDialog()
        
        
        # Get the image from the logic
        self.odmr_matrix_image = pg.ImageItem(self._odmr_logic.ODMR_plot_xy.transpose())
#        self.xy_odmr_image.setRect(Qt.Core.QRectF())
        self.odmr_image = pg.PlotDataItem(self._odmr_logic.ODMR_plot_x,self._odmr_logic.ODMR_plot_y)
        
        
        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.odmr_ViewWidget.addItem(self.odmr_image)
        self._mw.odmr_matrix_ViewWidget.addItem(self.odmr_matrix_image)
        
        # Connect the RadioButtons and connect to the events if they are clicked:
        self._mw.idle_StateWidget.toggled.connect(self.idle_clicked)
        self._mw.run_StateWidget.toggled.connect(self.run_clicked)
        
        ##
        ## Connect signals
        ##
        
        self._odmr_logic.signal_ODMR_plot_updated.connect(self.refresh_plot)
        self._odmr_logic.signal_ODMR_matrix_updated.connect(self.refresh_matrix)
        
        # Connect stop odmr
        self._odmr_logic.signal_ODMR_finished.connect(self._mw.idle_StateWidget.click)
        
        
        
         # Show the Main ODMR GUI:
        self._mw.show()



    def idle_clicked(self):
        """ Stopp the scan if the state has switched to idle. """
        self._odmr_logic.stop_ODMR_scan()
        self._odmr_logic.kill_ODMR()


    def run_clicked(self, enabled):
        """ Manages what happens if odmr scan is started.
        
        @param bool enabled: start scan if that is possible
        """
        
        #Firstly stop any scan that might be in progress
        self._odmr_logic.stop_ODMR_scan()
        self._odmr_logic.kill_ODMR()
        #Then if enabled. start a new odmr scan.
        if enabled:
            self._odmr_logic.start_ODMR()
            self._odmr_logic.start_ODMR_scan()

    def refresh_plot(self):
        ''' This method refreshes the xy-plot image
        '''
        self.odmr_image.setData(self._odmr_logic.ODMR_plot_x,self._odmr_logic.ODMR_plot_y)


        
    def refresh_matrix(self):
        ''' This method refreshes the xy-matrix image
        '''       
        self.odmr_matrix_image.setImage(self._odmr_logic.ODMR_plot_xy.transpose())
        
        
        

