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
from gui.TrackpointManager.TrackpointManagerGuiUI import Ui_TrackpointManager
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
  
          
            
class TrackpointManagerMainWindow(QtGui.QMainWindow,Ui_TrackpointManager):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        

            
               
            
class TrackpointManagerGui(Base,QtGui.QMainWindow,Ui_TrackpointManager):
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
        self._mw.set_tp_Button.clicked.connect(self.set_new_trackpoint)
        self._mw.goto_tp_Button.clicked.connect(self.goto_trackpoint)
        self._mw.delete_last_pos_Button.clicked.connect(self.delete_last_point)
        self._mw.manual_update_tp_Button.clicked.connect(self.manual_update_trackpoint)
        self._mw.tp_name_Input.editingFinished.connect(self.change_tp_name)
        self._mw.delete_tp_Button.clicked.connect(self.delete_trackpoint)
        
#        print('Main Trackpoint Manager Window shown:')
        self._mw.show()
    
    
    def set_new_trackpoint(self):
        ''' This method sets a new trackpoint from the current crosshair position

        '''
        key=self._tp_manager_logic.add_trackpoint()

        print('new trackpoint '+key)
        print(self._tp_manager_logic.get_all_trackpoints())
        print(self._tp_manager_logic.track_point_list[key].get_last_point())

        self.population_tp_list()
        
    def delete_last_point(self):
        ''' This method deletes the last track position of a chosen trackpoint
        '''
        
        key=self._mw.active_tp_Input.itemData(self._mw.active_tp_Input.currentIndex())
        self._tp_manager_logic.track_point_list[key].delete_last_point()

    def delete_trackpoint(self):
        '''This method deletes a trackpoint from the list of managed points
        '''
        key=self._mw.manage_tp_Input.itemData(self._mw.manage_tp_Input.currentIndex())
        self._tp_manager_logic.delete_trackpoint(trackpointname=key)
    
        self.population_tp_list()

    def manual_update_trackpoint(self):
        pass

    def goto_trackpoint(self, key):
        ''' Go to the last known position of trackpoint <key>
        '''
        
        key=self._mw.active_tp_Input.itemData(self._mw.active_tp_Input.currentIndex())

        self._tp_manager_logic.go_to_trackpoint(trackpointname=key)

        print(self._tp_manager_logic.track_point_list[key].get_last_point())


    def population_tp_list(self):
        ''' Populate the dropdown box for selecting a trackpoint
        '''
        self._mw.active_tp_Input.clear()
        self._mw.active_tp_Input.setInsertPolicy(QtGui.QComboBox.InsertAlphabetically)

        self._mw.manage_tp_Input.clear()
        self._mw.manage_tp_Input.setInsertPolicy(QtGui.QComboBox.InsertAlphabetically)
        
        for key in self._tp_manager_logic.track_point_list.keys():
            #self._tp_manager_logic.track_point_list[key].set_name('Kay_'+key[6:])
            if key is not 'crosshair':
                self._mw.active_tp_Input.addItem(self._tp_manager_logic.track_point_list[key].get_name(), key)
                self._mw.manage_tp_Input.addItem(self._tp_manager_logic.track_point_list[key].get_name(), key)

    def change_tp_name(self):
        '''Change the name of a trackpoint
        '''

        key=self._mw.manage_tp_Input.itemData(self._mw.manage_tp_Input.currentIndex())

        newname=self._mw.tp_name_Input.text()

        print(newname)

        self._tp_manager_logic.track_point_list[key].set_name(newname)

        self.population_tp_list()
