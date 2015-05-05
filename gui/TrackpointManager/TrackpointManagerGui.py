# -*- coding: utf-8 -*-
"""
Created on Tue May 5 2015

Lachlan Rogers
"""

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

from collections import OrderedDict
from core.Base import Base
from gui.TrackpointManager.TrackpointManagerGuiUI import Ui_MainWindow
from gui.Confocal.ConfocalGui import ColorBar





class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)

    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            #self.autoRange()
            self.setXRange(0,5)
            self.setYRange(0,10)

    def mouseDragEvent(self, ev,axis=0):
        if (ev.button() == QtCore.Qt.LeftButton) and (ev.modifiers() & QtCore.Qt.ControlModifier):
            pg.ViewBox.mouseDragEvent(self, ev,axis)
        else:
            ev.ignore()
  
          
            
class TrackpointManagerMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        

            
               
            
class TrackpointManagerGui(Base,QtGui.QMainWindow,Ui_MainWindow):
    """
    This is the GUI Class for TrackpointManager
    """
    
    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        
        self._modclass = 'TrackpointManagerGui'
        self._modtype = 'gui'
        
        ## declare connectors
        self.connector['in']['trackerlogic1'] = OrderedDict()
        self.connector['in']['trackerlogic1']['class'] = 'TrackpointManagerLogic'
        self.connector['in']['trackerlogic1']['object'] = None

#        self.connector['in']['savelogic'] = OrderedDict()
#        self.connector['in']['savelogic']['class'] = 'SaveLogic'
#        self.connector['in']['savelogic']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')  
                        
    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the Trackpoint Manager GUI.
          
          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        
        """
        
        self._tp_manager_logic = self.connector['in']['trackerlogic1']['object']
        print("Trackpoint Manager logic is", self._tp_manager_logic)
        
#        self._save_logic = self.connector['in']['savelogic']['object']
#        print("Save logic is", self._save_logic)  
        
        # Use the inherited class 'Ui_TrackpointManagerGuiTemplate' to create now the 
        # GUI element:
        self._mw = TrackpointManagerMainWindow()
                
        # Connect signals
        self.set_tp_Button.clicked.connect(self.set_new_trackpoint)
        
        print('Main Trackpoint Manager Window shown:')
        self._mw.show()
    
    
    def set_new_trackpoint(self):
        ''' This method sets a new trackpoint from the current crosshair position

        '''
        print("you have asked to set a trackpoint")
